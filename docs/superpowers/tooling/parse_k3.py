"""Parse the paid gpt-oss k=3 baseline (newmaster_gptoss_k3_run{1,2,3}).

Scores per-trial rob2_data.json against the OS reference CSV using the same
casefold-exact rule as the benchmark (compare_judgments). Distinguishes:
  scored  - rob2_data.json present
  FAILED  - trial subdir exists but no rob2_data.json (context overflow etc.)
  missing - no subdir at all
Agreement is computed over the COMMON set (trials scored in all 3 runs) so the
three runs share one denominator. Tolerant of partial data mid-run.
"""
import csv
import json
import re
from pathlib import Path
from statistics import mean

REPO = Path("C:/Users/zaida/auto-rob2")
LOGDIR = Path("C:/Users/zaida/AppData/Local/Temp/claude/C--Users-zaida-auto-rob2/fca83bbb-f11a-4757-bb02-4767eef7d436/scratchpad/logs")
RUNS = [1, 2, 3]
TRIALS = ["ARASENS", "ARCHES", "CHAARTED", "ENZAMET", "LATITUDE", "PEACE-1", "STAMPEDE", "TITAN"]
DOMAINS = ["D1", "D2", "D3", "D4", "D5"]
# Old postmerge baseline (pre-rewrite, 8 trials) from the inbox - NOT same trial set.
OLD_BASELINE = {"D1": 100.0, "D2": 75.0, "D3": 75.0, "D4": 100.0, "D5": 87.5}


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
    sub = REPO / f"outputs/benchmark/newmaster_gptoss_k3_run{run}/{trial}_os"
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


def overflow_tokens(trial):
    """Largest requested-token count seen for a failed trial, from err logs."""
    best = 0
    for run in RUNS:
        err = LOGDIR / f"run{run}.err"
        if not err.exists():
            continue
        txt = err.read_text(encoding="utf-8", errors="ignore")
        # find the failure block for this trial and the token counts near it
        for m in re.finditer(r"you requested about (\d+) tokens", txt):
            best = max(best, int(m.group(1)))
    return best


def main():
    ref = load_reference()
    def ref_of(t):
        return ref.get(t.casefold(), {})

    # status[run][trial] = (state, data-or-None); results[run][trial] = parsed
    status = {r: {} for r in RUNS}
    results = {r: {} for r in RUNS}
    for r in RUNS:
        for t in TRIALS:
            st, path = trial_status(r, t)
            status[r][t] = st
            if st == "scored":
                results[r][t] = load_trial(path)

    # classify trials
    scored_all = [t for t in TRIALS if all(status[r][t] == "scored" for r in RUNS)]
    failed_any = [t for t in TRIALS if any(status[r][t] == "FAILED" for r in RUNS)]

    print("=== run completion ===")
    for r in RUNS:
        sc = [t for t in TRIALS if status[r][t] == "scored"]
        fl = [t for t in TRIALS if status[r][t] == "FAILED"]
        ms = [t for t in TRIALS if status[r][t] == "missing"]
        print(f"run{r}: scored={len(sc)} {sc} | FAILED={fl} | missing={ms}")
    print(f"\nCOMMON SCOREABLE SET (scored in all 3 runs): {scored_all}  (n={len(scored_all)})")
    print(f"FAILED in >=1 run: {failed_any}")
    for t in failed_any:
        tok = overflow_tokens(t)
        print(f"   {t}: context overflow, peak requested ~{tok:,} tok (limit 131,072)")
    print()

    S = scored_all  # score only the common set for a clean k=3

    print(f"=== per-domain agreement per run over COMMON set (n={len(S)}: {S}) ===")
    per_run = {r: {} for r in RUNS}
    for r in RUNS:
        for d in DOMAINS + ["Overall"]:
            tot = matched = 0
            for t in S:
                pred = results[r][t]["overall"] if d == "Overall" else results[r][t]["final"][d]
                gold = ref_of(t).get(d, "")
                if not gold:
                    continue
                tot += 1
                matched += 1 if pred == gold else 0
            per_run[r][d] = (100.0 * matched / tot) if tot else None
        row = "  ".join(f"{d}={('NA' if per_run[r][d] is None else format(per_run[r][d],'.0f'))}"
                        for d in DOMAINS + ["Overall"])
        print(f"run{r}: {row}")
    print()

    print("=== across-run: mean [range] | runs | vs OLD 8-trial baseline (NOT same trial set) ===")
    for d in DOMAINS + ["Overall"]:
        vals = [per_run[r][d] for r in RUNS if per_run[r][d] is not None]
        if not vals:
            print(f"{d}: NA"); continue
        rng = max(vals) - min(vals)
        old = OLD_BASELINE.get(d)
        cmp = "" if old is None else f" | old={old:.0f} (different 8-trial set)"
        print(f"{d}: mean={mean(vals):.0f}  range={rng:.0f}  runs={[round(v) for v in vals]}{cmp}")
    print()

    print(f"=== per-trial x domain over common set: [r1 r2 r3] (ref) -> TAG ===")
    rollup = {d: {"stable-correct": 0, "stable-wrong": 0, "noisy": 0} for d in DOMAINS}
    for t in S:
        gold = ref_of(t)
        print(f"\n-- {t} -- (ref " + " ".join(f"{d}={short(gold.get(d,''))}" for d in DOMAINS) +
              f" | Overall={short(gold.get('Overall',''))})")
        for d in DOMAINS:
            labels = [results[r][t]["final"][d] for r in RUNS]
            g = gold.get(d, "")
            if len(set(labels)) == 1:
                tag = "stable-correct" if labels[0] == g else "stable-wrong"
            else:
                tag = "noisy"
            rollup[d][tag] += 1
            print(f"   {d}: [{' '.join(short(x) for x in labels)}] (ref {short(g)}) -> {tag}")
    print("\n=== domain tag rollup over common set ===")
    for d in DOMAINS:
        print(f"{d}: {rollup[d]}")

    print("\n=== headline trials: PEACE-1 + TITAN (full domain+overall) ===")
    for t in ["PEACE-1", "TITAN"]:
        if t not in S:
            print(f"-- {t} -- not in common set (status: " +
                  ", ".join(f"run{r}={status[r][t]}" for r in RUNS) + ")")
            continue
        gold = ref_of(t)
        print(f"-- {t} --")
        for d in DOMAINS + ["Overall"]:
            labels = [results[r][t]["overall"] if d == "Overall" else results[r][t]["final"][d] for r in RUNS]
            print(f"   {d}: [{' '.join(short(x) for x in labels)}] (ref {short(gold.get(d,''))})")

    print("\n=== adjudication flips (initial -> final) on scored trials ===")
    for r in RUNS:
        for t in TRIALS:
            if t not in results[r]:
                continue
            fin, ini = results[r][t]["final"], results[r][t]["initial"]
            flips = [f"{d}:{short(ini[d])}->{short(fin[d])}" for d in DOMAINS
                     if ini[d] and fin[d] and ini[d] != fin[d]]
            if flips:
                print(f"run{r} {t}: {', '.join(flips)}")


if __name__ == "__main__":
    main()
