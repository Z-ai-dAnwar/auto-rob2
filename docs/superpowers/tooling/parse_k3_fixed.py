"""Score the POST-FIX paid gpt-oss k=3 run (fixed_gptoss_k3_run{1,2,3}).

Adapted from parse_k3.py for the supplement context-overflow fix
(ADR-0006). Differences from the original:
  - Reads outputs/benchmark/fixed_gptoss_k3_run{run}/{trial}_os/ (post-fix dirs).
  - Reports per-domain agreement over TWO sets:
      (a) the full common scoreable set (the new real 8-trial baseline), and
      (b) the 5 previously-passing trials only (ARASENS/CHAARTED/LATITUDE/
          PEACE-1/TITAN) - the apples-to-apples no-regression comparison
          against the pre-fix baseline, since the pre-fix numbers were
          computed over only those 5 (ARCHES/ENZAMET/STAMPEDE overflowed).
  - Prints a per-domain delta of the 5-trial subset vs the pre-fix baseline
    and a clear no-regression verdict.

Scores domain_judgments (final) against the OS reference CSV using the same
casefold-exact rule as the benchmark. Tolerant of partial data mid-run.
"""
import csv
import json
import os
from pathlib import Path
from statistics import mean

REPO = Path("C:/Users/zaida/auto-rob2")
# Output-dir prefix for the run set to score. Default = the 8000-char-cap run;
# override for the cap=16000 experiment, e.g. K3_PREFIX=fixed16k_gptoss_k3_run.
PREFIX = os.getenv("K3_PREFIX", "fixed_gptoss_k3_run")
RUNS = [1, 2, 3]
TRIALS = ["ARASENS", "ARCHES", "CHAARTED", "ENZAMET", "LATITUDE", "PEACE-1", "STAMPEDE", "TITAN"]
DOMAINS = ["D1", "D2", "D3", "D4", "D5"]

# The 5 trials that scored pre-fix (did NOT overflow the 131k context window).
PREV_PASSING = ["ARASENS", "CHAARTED", "LATITUDE", "PEACE-1", "TITAN"]
# The 3 trials that FAILED pre-fix on the context limit.
PREV_FAILED = ["ARCHES", "ENZAMET", "STAMPEDE"]
# Pre-fix per-domain agreement over the 5 PREV_PASSING trials (the baseline to beat).
PRE_FIX_5TRIAL_BASELINE = {"D1": 93.0, "D2": 87.0, "D3": 67.0, "D4": 100.0, "D5": 80.0}


def norm(j):
    if j is None:
        return ""
    s = " ".join(str(j).split()).casefold()
    m = {"l": "Low", "low": "Low", "s": "Some concerns",
         "some concerns": "Some concerns", "h": "High", "high": "High"}
    return m.get(s, str(j).strip())


def short(label):
    return {"Low": "L", "Some concerns": "SC", "High": "H", "": "-"}.get(norm(label), norm(label))


def load_reference():
    ref = {}
    with open(REPO / "data/references/overall_survival.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            t = (row.get("Trial") or "").strip()
            if not t:
                continue
            entry = {d: norm(row.get(d)) for d in DOMAINS}
            entry["Overall"] = norm(row.get("Overall Risk"))
            ref[t.casefold()] = entry
    return ref


def trial_status(run, trial):
    sub = REPO / f"outputs/benchmark/{PREFIX}{run}/{trial}_os"
    data = sub / f"{trial}_rob2_data.json"
    if data.exists():
        return "scored", data
    if sub.exists():
        return "FAILED", None
    return "missing", None


def load_trial(path):
    d = json.loads(path.read_text(encoding="utf-8"))
    final = {dm: norm((d.get("domain_judgments") or {}).get(dm)) for dm in DOMAINS}
    initial = {dm: norm((d.get("initial_domain_judgments") or {}).get(dm)) for dm in DOMAINS}
    return {"final": final, "initial": initial, "overall": norm(d.get("overall_judgment"))}


def agreement_over(trials, results, ref_of):
    """Per-run, per-domain agreement (%) over the given trial subset.
    Returns {run: {domain: pct-or-None}}."""
    per_run = {r: {} for r in RUNS}
    for r in RUNS:
        for d in DOMAINS + ["Overall"]:
            tot = matched = 0
            for t in trials:
                if t not in results[r]:
                    continue
                pred = results[r][t]["overall"] if d == "Overall" else results[r][t]["final"][d]
                gold = ref_of(t).get(d, "")
                if not gold:
                    continue
                tot += 1
                matched += 1 if pred == gold else 0
            per_run[r][d] = (100.0 * matched / tot) if tot else None
    return per_run


def mean_range(per_run, domain):
    vals = [per_run[r][domain] for r in RUNS if per_run[r].get(domain) is not None]
    if not vals:
        return None, None, []
    return mean(vals), max(vals) - min(vals), [round(v) for v in vals]


def main():
    ref = load_reference()
    def ref_of(t):
        return ref.get(t.casefold(), {})

    status = {r: {} for r in RUNS}
    results = {r: {} for r in RUNS}
    for r in RUNS:
        for t in TRIALS:
            st, path = trial_status(r, t)
            status[r][t] = st
            if st == "scored":
                results[r][t] = load_trial(path)

    scored_all = [t for t in TRIALS if all(status[r][t] == "scored" for r in RUNS)]

    print("=== run completion ===")
    for r in RUNS:
        sc = [t for t in TRIALS if status[r][t] == "scored"]
        fl = [t for t in TRIALS if status[r][t] == "FAILED"]
        ms = [t for t in TRIALS if status[r][t] == "missing"]
        print(f"run{r}: scored={len(sc)} {sc} | FAILED={fl} | missing={ms}")

    print(f"\nCOMMON SCOREABLE SET (scored in all 3 runs): {scored_all} (n={len(scored_all)})")
    rescued = [t for t in PREV_FAILED if all(status[r][t] == "scored" for r in RUNS)]
    print(f"Previously-FAILED trials now scoring in all 3 runs: {rescued} "
          f"({len(rescued)}/{len(PREV_FAILED)})")

    # (a) Full common set: the new real baseline.
    print(f"\n=== (A) NEW 8-TRIAL BASELINE: per-domain agreement over common set "
          f"(n={len(scored_all)}) ===")
    full = agreement_over(scored_all, results, ref_of)
    for r in RUNS:
        row = "  ".join(
            f"{d}={'NA' if full[r][d] is None else format(full[r][d], '.0f')}"
            for d in DOMAINS + ["Overall"])
        print(f"run{r}: {row}")
    print("across-run mean [range]:")
    for d in DOMAINS + ["Overall"]:
        m, rng, vals = mean_range(full, d)
        print(f"  {d}: {'NA' if m is None else f'mean={m:.0f} range={rng:.0f} runs={vals}'}")

    # (b) 5 previously-passing trials: no-regression comparison.
    present_prev = [t for t in PREV_PASSING if all(status[r][t] == "scored" for r in RUNS)]
    print(f"\n=== (B) NO-REGRESSION CHECK: 5 previously-passing trials "
          f"{present_prev} vs pre-fix baseline ===")
    sub = agreement_over(present_prev, results, ref_of)
    for r in RUNS:
        row = "  ".join(
            f"{d}={'NA' if sub[r][d] is None else format(sub[r][d], '.0f')}"
            for d in DOMAINS)
        print(f"run{r}: {row}")
    print(f"{'domain':<8}{'pre-fix':>8}{'post mean':>11}{'delta':>8}   verdict")
    regressions = []
    for d in DOMAINS:
        m, rng, vals = mean_range(sub, d)
        base = PRE_FIX_5TRIAL_BASELINE[d]
        if m is None:
            print(f"{d:<8}{base:>8.0f}{'NA':>11}{'NA':>8}   no data")
            continue
        delta = m - base
        ok = m >= base - 0.5  # unchanged-or-better (0.5 tolerance for rounding)
        if not ok:
            regressions.append((d, base, m))
        print(f"{d:<8}{base:>8.0f}{m:>11.0f}{delta:>+8.0f}   "
              f"{'OK' if ok else 'REGRESSION'}  (runs={vals}, range={rng:.0f})")

    print("\n=== ACCEPTANCE ===")
    all8 = len(scored_all) == len(TRIALS)
    print(f"  all 8 trials score in all 3 runs: {all8} ({len(scored_all)}/8)")
    print(f"  3 previously-failed now score:    {len(rescued) == len(PREV_FAILED)} "
          f"({len(rescued)}/3)")
    print(f"  no per-domain regression on the 5: {not regressions}"
          + ("" if not regressions else f"  REGRESSIONS: {regressions}"))
    verdict = all8 and len(rescued) == len(PREV_FAILED) and not regressions
    print(f"\n  OVERALL: {'PASS' if verdict else 'NOT YET PASS'}")

    # Per-trial x domain detail (stability) over the common set.
    print(f"\n=== per-trial x domain over common set: [r1 r2 r3] (ref) -> tag ===")
    for t in scored_all:
        gold = ref_of(t)
        print(f"\n-- {t} -- (ref " + " ".join(f"{d}={short(gold.get(d, ''))}" for d in DOMAINS)
              + f" | Overall={short(gold.get('Overall', ''))})")
        for d in DOMAINS:
            labels = [results[r][t]["final"][d] for r in RUNS]
            g = gold.get(d, "")
            if len(set(labels)) == 1:
                tag = "stable-correct" if labels[0] == g else "stable-wrong"
            else:
                tag = "noisy"
            print(f"   {d}: [{' '.join(short(x) for x in labels)}] (ref {short(g)}) -> {tag}")


if __name__ == "__main__":
    main()
