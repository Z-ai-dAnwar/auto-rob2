<#
.SYNOPSIS
    Single entry point for RoB 2 benchmark runs. Detaches from the terminal,
    streams to a log file, and writes a done-marker with a result summary.

.DESCRIPTION
    Replaces the four near-duplicate watchdog scripts that lived under
    outputs\benchmark\logs\. Those were gitignored (.gitignore:56 ignores
    outputs/*), so the tooling that launched every benchmark this project ever
    ran was never version controlled. This one lives in scripts\ and is tracked.

    Three things it guarantees:

      1. The run survives the terminal closing. It registers itself as a
         Windows scheduled task and starts that, so the work runs under the
         Task Scheduler service with no tie to any console or job object.
         Start-Process -WindowStyle Hidden usually survives too, but dies if
         the parent shell sits in a job object with kill-on-close; a scheduled
         task has no such relationship.
      2. Everything is logged to a file as it happens, not buffered to the end.
      3. A done-marker is written when the run finishes, INCLUDING when it
         fails or times out. The marker is the thing a later session reads to
         find out what happened, so it is written in a finally block.

    Repo root is derived from $PSScriptRoot, not hardcoded, so moving the
    repository does not break this script.

.PARAMETER Prefix
    Names the run. Output goes to outputs\benchmark\<Prefix><n> for n in
    1..K, logs to outputs\benchmark\logs\<Prefix>*, done-marker to
    outputs\benchmark\<Prefix>.DONE.json and .DONE.md.

.PARAMETER K
    Number of sequential passes over the trial set (k-voting). Each pass is a
    full benchmark run and costs real money.

.PARAMETER DryRun
    Passes --dry-run to benchmark.py: validates inputs and prints the planned
    runs without calling any model. Costs nothing. Use this to verify the
    detach/log/marker plumbing before spending.

.PARAMETER Foreground
    Run inline in the current shell instead of detaching. For debugging.

.EXAMPLE
    # Verify the plumbing, zero spend:
    powershell -File scripts\run_benchmark.ps1 -Prefix smoke -K 1 -DryRun

.EXAMPLE
    # Full 8-trial, k=5 run, detached:
    powershell -File scripts\run_benchmark.ps1 -Prefix kvote_run -K 5

.EXAMPLE
    # A subset of trials. NOTE the commas: under powershell -File, an array
    # parameter takes one token, so space-separated values silently fall
    # through to the next positional parameter. PositionalBinding is off so
    # that mistake errors instead of binding somewhere wrong.
    powershell -File scripts\run_benchmark.ps1 -Prefix smoke -K 1 -Trials CHAARTED:OS,ARASENS:OS

.EXAMPLE
    # Check on a detached run later, from a fresh terminal:
    powershell -File scripts\run_benchmark.ps1 -Status kvote_run
#>

[CmdletBinding(PositionalBinding = $false)]
param(
    [string]$Prefix = 'run',

    [int]$K = 1,

    [int]$StartRun = 1,

    [string[]]$Trials = @(
        'ARASENS:OS', 'ARCHES:OS', 'CHAARTED:OS', 'ENZAMET:OS',
        'LATITUDE:OS', 'PEACE-1:OS', 'STAMPEDE:OS', 'TITAN:OS'
    ),

    # Hard kill-timer per pass. providers/openrouter.py has no socket timeout,
    # so a stalled connection would otherwise block forever.
    [int]$TimeoutMin = 150,

    [string]$Provider = 'openrouter',

    [string]$Model = 'openai/gpt-oss-120b',

    # The default 190/18 makes the rate limiter SLEEP and stall near trial 8.
    # This is not a 429; it is our own limiter pausing. Shell env wins over
    # .env because config.py calls load_dotenv(override=False).
    [string]$RpdLimit = '3000',

    [string]$RpmLimit = '60',

    [switch]$NoSupplements,

    [switch]$DryRun,

    [switch]$Foreground,

    # Report on an existing run and exit. Does not start anything.
    [string]$Status,

    # Internal. Set when the scheduled task re-enters this script.
    [switch]$Child
)

$ErrorActionPreference = 'Continue'

# Under `powershell -File`, an array parameter swallows exactly one token, so
# `-Trials A,B` arrives as the single string "A,B" and `-Trials A B` sends B to
# the next positional parameter. Normalize here so both forms work and neither
# reaches benchmark.py malformed.
$Trials = @(
    $Trials |
        ForEach-Object { $_ -split ',' } |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ -ne '' }
)

$RepoRoot   = Split-Path -Parent $PSScriptRoot
$BenchDir   = Join-Path $RepoRoot 'outputs\benchmark'
$LogDir     = Join-Path $BenchDir 'logs'
$PythonExe  = Join-Path $RepoRoot '.venv\Scripts\python.exe'


function Get-MarkerPath { param([string]$P) Join-Path $BenchDir "$P.DONE.json" }
function Get-StatusLog  { param([string]$P) Join-Path $LogDir  "$P.status.log" }


# ---------------------------------------------------------------- -Status ----
# Read-only report on a run, for checking back from a fresh session.
if ($Status) {
    $marker    = Get-MarkerPath $Status
    $statusLog = Get-StatusLog  $Status

    if (Test-Path $marker) {
        Write-Host "Run '$Status' is FINISHED. Marker:" -ForegroundColor Green
        Write-Host $marker
        Write-Host ''
        Get-Content (Join-Path $BenchDir "$Status.DONE.md") -ErrorAction SilentlyContinue
    }
    else {
        $task = Get-ScheduledTask -TaskName "AutoRob2-Benchmark-$Status" -ErrorAction SilentlyContinue
        if ($task) {
            Write-Host "Run '$Status' is IN PROGRESS (scheduled task state: $($task.State))." -ForegroundColor Yellow
        }
        else {
            Write-Host "No done-marker and no scheduled task for '$Status'." -ForegroundColor Red
            Write-Host "It either never started or died without writing a marker."
        }
        if (Test-Path $statusLog) {
            Write-Host ''
            Write-Host "--- last 25 lines of $statusLog ---"
            Get-Content $statusLog -Tail 25
        }
    }
    return
}


# ---------------------------------------------------------------- detach ----
# Register as a scheduled task and start it, then return immediately. The task
# is registered with no trigger and started explicitly, which sidesteps every
# trigger-timing problem.
if (-not $Child -and -not $Foreground) {
    $taskName = "AutoRob2-Benchmark-$Prefix"

    $marker = Get-MarkerPath $Prefix
    if (Test-Path $marker) {
        Write-Host "A done-marker already exists for '$Prefix':" -ForegroundColor Yellow
        Write-Host "  $marker"
        Write-Host "Delete it, or pick a different -Prefix, then run again."
        return
    }

    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existing) {
        if ($existing.State -eq 'Running') {
            Write-Host "Run '$Prefix' is already running. Use -Status $Prefix to check it." -ForegroundColor Yellow
            return
        }
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }

    # Rebuild this invocation for the child, with -Child added.
    $childArgs = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', "`"$PSCommandPath`"",
        '-Child',
        '-Prefix', $Prefix,
        '-K', $K,
        '-StartRun', $StartRun,
        '-TimeoutMin', $TimeoutMin,
        '-Provider', $Provider,
        '-Model', $Model,
        '-RpdLimit', $RpdLimit,
        '-RpmLimit', $RpmLimit
    )
    if ($NoSupplements) { $childArgs += '-NoSupplements' }
    if ($DryRun)        { $childArgs += '-DryRun' }
    # Comma-joined, not space-separated: see the -Trials note in the examples.
    $childArgs += @('-Trials', ($Trials -join ','))

    $action = New-ScheduledTaskAction -Execute 'powershell.exe' `
        -Argument ($childArgs -join ' ') -WorkingDirectory $RepoRoot

    # ExecutionTimeLimit 0 = no limit. The per-pass kill-timer inside the child
    # is the real timeout; the scheduler must not second-guess it.
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew `
        -StartWhenAvailable

    $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" `
        -LogonType Interactive -RunLevel Limited

    Register-ScheduledTask -TaskName $taskName -Action $action `
        -Settings $settings -Principal $principal `
        -Description "auto-rob2 benchmark run '$Prefix'" | Out-Null

    Start-ScheduledTask -TaskName $taskName

    Write-Host "Detached run started." -ForegroundColor Green
    Write-Host "  prefix       : $Prefix  (k=$K, $($Trials.Count) trials$(if ($DryRun) { ', DRY RUN, no spend' }))"
    Write-Host "  task         : $taskName"
    Write-Host "  live log     : $(Get-StatusLog $Prefix)"
    Write-Host "  done-marker  : $(Get-MarkerPath $Prefix)"
    Write-Host ''
    Write-Host "You can close this terminal. Check back with:"
    Write-Host "  powershell -File scripts\run_benchmark.ps1 -Status $Prefix"
    return
}


# ------------------------------------------------------------ the actual run ----
Set-Location $RepoRoot
New-Item -ItemType Directory -Force $LogDir | Out-Null

$statusLog = Get-StatusLog $Prefix
$marker    = Get-MarkerPath $Prefix
$markerMd  = Join-Path $BenchDir "$Prefix.DONE.md"

$env:ROB2_PROVIDER  = $Provider
$env:ROB2_MODEL     = $Model
$env:ROB2_RPD_LIMIT = $RpdLimit
$env:ROB2_RPM_LIMIT = $RpmLimit

function Stamp {
    param([string]$Message)
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $Message"
    Add-Content -Path $statusLog -Value $line -Encoding utf8
    Write-Host $line
}

$startedAt = Get-Date
$passes    = @()

# Recorded so a result can be traced back to the code that produced it.
$gitCommit = (& git -C $RepoRoot rev-parse HEAD 2>$null)
$gitBranch = (& git -C $RepoRoot rev-parse --abbrev-ref HEAD 2>$null)
$gitDirty  = [bool](& git -C $RepoRoot status --porcelain 2>$null)

try {
    Stamp "=== START '$Prefix' | k=$K (runs $StartRun..$K) | $($Trials.Count) trials | $Provider/$Model | RPD=$RpdLimit RPM=$RpmLimit | dry-run=$($DryRun.IsPresent) ==="
    Stamp "commit $gitCommit on $gitBranch (working tree dirty: $gitDirty)"

    foreach ($n in $StartRun..$K) {
        $outDir     = Join-Path $BenchDir "$Prefix$n"
        $outLog     = Join-Path $LogDir "$Prefix$n.out.log"
        $errLog     = Join-Path $LogDir "$Prefix$n.err.log"
        $resultJson = Join-Path $outDir 'benchmark_results.json'
        $passStart  = Get-Date

        # Idempotency: a finished pass is never re-run, so relaunching after a
        # crash continues from the right place instead of redoing paid work.
        # An incomplete leftover is wiped first so the scorer can never mix
        # stale trial judgments with new ones.
        if (Test-Path $resultJson) {
            Stamp "RUN$n SKIP  -> already complete ($outDir)"
            $passes += [pscustomobject]@{ run = $n; status = 'skipped-complete'; output_dir = "$outDir"; minutes = 0 }
            continue
        }
        if (Test-Path $outDir) {
            Stamp "RUN$n CLEAN -> removing incomplete $outDir"
            Remove-Item -Recurse -Force $outDir -ErrorAction SilentlyContinue
        }

        $argList = @('benchmark.py', '--outcome-map') + $Trials + @('--output-dir', $outDir, '--no-cache')
        if (-not $NoSupplements) {
            $argList += @('--use-supplements', '--supplement-dir', 'inputs/benchmark/supplement')
        }
        if ($DryRun) { $argList += '--dry-run' }

        Stamp "RUN$n START -> $outDir"
        $proc = Start-Process -FilePath $PythonExe -ArgumentList $argList `
            -RedirectStandardOutput $outLog -RedirectStandardError $errLog `
            -NoNewWindow -PassThru

        # Touching .Handle caches the OS process handle. Without it, the object
        # Start-Process returns never opened one, and reading .ExitCode after
        # the child dies throws "Process was not started by this object" -- so
        # a successful run gets recorded with a null exit code and misjudged.
        $null = $proc.Handle

        $timedOut = $false
        if (-not $proc.WaitForExit($TimeoutMin * 60 * 1000)) {
            $timedOut = $true
            Stamp "RUN$n TIMEOUT after $TimeoutMin min -> killing PID $($proc.Id)"
            # taskkill /T does a real process-tree kill on PowerShell 5.1,
            # where Process.Kill($true) is unavailable (.NET 5+ only).
            & taskkill /PID $proc.Id /T /F 2>$null | Out-Null
            try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
            Start-Sleep -Seconds 5
        }

        $minutes = [math]::Round(((Get-Date) - $passStart).TotalMinutes, 1)

        # Start-Process -PassThru leaves ExitCode unpopulated until the object
        # is refreshed, so without this the marker records a blank exit code.
        $exitCode = $null
        if (-not $timedOut) {
            try {
                $proc.WaitForExit()
                $exitCode = $proc.ExitCode
            }
            catch { $exitCode = $null }
        }

        if ($DryRun) {
            # Check the exit code BEFORE reporting success. A dry run that
            # crashed must not produce a healthy-looking marker.
            if ($exitCode -eq 0) {
                $state = 'dry-run'
                Stamp "RUN$n DRYRUN ok in $minutes min (exit 0)"
            }
            else {
                $state = 'dry-run-failed'
                Stamp "RUN$n DRYRUN FAILED in $minutes min (exit $exitCode) -- see $errLog"
            }
        }
        elseif (Test-Path $resultJson) {
            $state = 'complete'
            Stamp "RUN$n DONE  -> benchmark_results.json present ($minutes min)"
        }
        elseif ($timedOut) {
            $state = 'timeout'
            Stamp "RUN$n FAILED-> timed out, no benchmark_results.json"
        }
        else {
            $state = 'incomplete'
            Stamp "RUN$n FAILED-> exited (code $exitCode) with no benchmark_results.json"
        }

        $passes += [pscustomobject]@{
            run        = $n
            status     = $state
            output_dir = "$outDir"
            minutes    = $minutes
            exit_code  = $exitCode
        }
    }
}
catch {
    Stamp "FATAL: $($_.Exception.Message)"
}
finally {
    # The marker is written no matter how we got here. A run that died is
    # exactly the case where a later session most needs to know what happened.
    $endedAt = Get-Date

    # Pull the headline numbers out of whichever passes completed.
    $perPassSummary = @()
    foreach ($p in $passes) {
        $rj = Join-Path $p.output_dir 'benchmark_results.json'
        if (Test-Path $rj) {
            try {
                $parsed = Get-Content $rj -Raw | ConvertFrom-Json
                $rates  = @{}
                foreach ($prop in $parsed.summary.agreement_rates.PSObject.Properties) {
                    $rates[$prop.Name] = $prop.Value
                }
                $perPassSummary += [pscustomobject]@{
                    run              = $p.run
                    evaluated_trials = $parsed.summary.evaluated_trials
                    agreement_rates  = $rates
                }
            }
            catch {
                $perPassSummary += [pscustomobject]@{ run = $p.run; parse_error = "$($_.Exception.Message)" }
            }
        }
    }

    $completed = @($passes | Where-Object { $_.status -eq 'complete' -or $_.status -eq 'skipped-complete' }).Count
    $failed    = @($passes | Where-Object { $_.status -in @('timeout', 'incomplete', 'dry-run-failed') }).Count

    $summaryObj = [pscustomobject]@{
        prefix            = $Prefix
        started_at        = $startedAt.ToString('o')
        ended_at          = $endedAt.ToString('o')
        duration_minutes  = [math]::Round(($endedAt - $startedAt).TotalMinutes, 1)
        dry_run           = $DryRun.IsPresent
        k                 = $K
        trials            = $Trials
        provider          = $Provider
        model             = $Model
        rpd_limit         = $RpdLimit
        rpm_limit         = $RpmLimit
        supplements       = (-not $NoSupplements)
        git_commit        = "$gitCommit"
        git_branch        = "$gitBranch"
        git_dirty         = $gitDirty
        passes_completed  = $completed
        passes_failed     = $failed
        passes            = $passes
        per_pass_summary  = $perPassSummary
        status_log        = "$statusLog"
    }

    $summaryObj | ConvertTo-Json -Depth 8 | Set-Content -Path $marker -Encoding utf8

    # Human-readable twin. Read this one first.
    $md = New-Object System.Text.StringBuilder
    [void]$md.AppendLine("# Benchmark run '$Prefix'")
    [void]$md.AppendLine('')
    [void]$md.AppendLine("- finished: $($endedAt.ToString('yyyy-MM-dd HH:mm:ss'))")
    [void]$md.AppendLine("- duration: $([math]::Round(($endedAt - $startedAt).TotalMinutes, 1)) min")
    [void]$md.AppendLine("- passes: $completed complete, $failed failed (k=$K)")
    [void]$md.AppendLine("- model: $Provider/$Model")
    [void]$md.AppendLine("- commit: $gitCommit on $gitBranch (dirty: $gitDirty)")
    if ($DryRun) { [void]$md.AppendLine('- DRY RUN: no model was called, no money was spent.') }
    [void]$md.AppendLine('')

    if ($perPassSummary.Count -gt 0) {
        [void]$md.AppendLine('## Per-pass agreement')
        [void]$md.AppendLine('')
        [void]$md.AppendLine('| pass | trials | D1 | D2 | D3 | D4 | D5 | Overall |')
        [void]$md.AppendLine('| --- | --- | --- | --- | --- | --- | --- | --- |')
        foreach ($s in $perPassSummary) {
            if ($s.PSObject.Properties.Name -contains 'parse_error') {
                [void]$md.AppendLine("| $($s.run) | PARSE ERROR: $($s.parse_error) | | | | | | |")
                continue
            }
            $c = @()
            foreach ($d in @('D1', 'D2', 'D3', 'D4', 'D5', 'Overall')) {
                if ($null -ne $s.agreement_rates[$d]) { $c += ('{0:P0}' -f $s.agreement_rates[$d]) } else { $c += '-' }
            }
            [void]$md.AppendLine("| $($s.run) | $($s.evaluated_trials) | $($c -join ' | ') |")
        }
        [void]$md.AppendLine('')
        [void]$md.AppendLine('> Read these against the trivial baseline before drawing any conclusion.')
        [void]$md.AppendLine('> The reference set is 81% one class ("Low") with zero "High" judgments, so')
        [void]$md.AppendLine('> answering "Low" to everything without reading a word scores D1 100 / D2 90 /')
        [void]$md.AppendLine('> D3 70 / D4 100 / D5 80 / Overall 100. With n=10, one flip = 10 points.')
        [void]$md.AppendLine('> A percentage here is not evidence of anything on its own.')
        [void]$md.AppendLine('')
    }

    [void]$md.AppendLine('## Passes')
    [void]$md.AppendLine('')
    foreach ($p in $passes) {
        [void]$md.AppendLine("- run $($p.run): **$($p.status)** ($($p.minutes) min, exit $($p.exit_code)) -> $($p.output_dir)")
    }
    [void]$md.AppendLine('')
    [void]$md.AppendLine("Full log: ``$statusLog``")

    Set-Content -Path $markerMd -Value $md.ToString() -Encoding utf8

    Stamp "=== END '$Prefix' | $completed complete, $failed failed | marker: $marker ==="
}
