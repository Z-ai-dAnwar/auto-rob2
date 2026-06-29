"""k-vote (self-consistency) scorer for the RoB 2 benchmark.

Reads k benchmark run directories, majority-votes each trial's per-domain
judgement via ``rob2_pipeline.self_consistency``, scores the voted label against
the reference, and prints per-domain voted agreement plus a per-domain
instability map and a before/after vs the k=3 baseline.

This is an OUTER aggregation layer: it only reads the per-run JSON the pipeline
already wrote. It never re-runs an assessment and touches no judge, no skip/NA
logic, and no part of the RoB 2 algorithm.

Run (after the watchdog has produced outputs/benchmark/<prefix>1..k):
    uv run python docs/superpowers/tooling/kvote_score.py --prefix kvote_run --k 5
    uv run python docs/superpowers/tooling/kvote_score.py --prefix kvote_smoke --k 5 \
        --trials CHAARTED
"""

import argparse
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from rob2_pipeline.self_consistency import (  # noqa: E402
    _normalize,
    collect_trial_votes,
    summarize_domain_votes,
)

DOMAINS = ["D1", "D2", "D3", "D4", "D5"]
TRIALS_8 = [
    "ARASENS",
    "ARCHES",
    "CHAARTED",
    "ENZAMET",
    "LATITUDE",
    "PEACE-1",
    "STAMPEDE",
    "TITAN",
]
# Prior k=3 baseline = MEAN per-run agreement across 3 runs (not a vote). Kept
# for the before/after, with the metric difference called out in the output.
K3_BASELINE = {"D1": 88, "D2": 92, "D3": 62, "D4": 100, "D5": 79}


def load_reference(csv_path: Path) -> dict[str, dict[str, str]]:
    ref: dict[str, dict[str, str]] = {}
    with open(csv_path, newline="") as fh:
        for row in csv.DictReader(fh):
            trial = row["Trial"].strip()
            ref[trial] = {d: row[d].strip() for d in DOMAINS}
    return ref


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", default="kvote_run")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--output-root", default=str(REPO / "outputs" / "benchmark"))
    parser.add_argument(
        "--reference",
        default=str(REPO / "data" / "references" / "overall_survival.csv"),
    )
    parser.add_argument("--trials", nargs="+", default=TRIALS_8)
    args = parser.parse_args()

    output_root = Path(args.output_root)
    run_dirs = [output_root / f"{args.prefix}{n}" for n in range(1, args.k + 1)]
    present_dirs = [d for d in run_dirs if d.is_dir()]
    print(f"k-vote scorer: prefix={args.prefix} k={args.k}")
    print(f"  run dirs present: {len(present_dirs)}/{args.k}")
    for d in run_dirs:
        print(f"    {'OK ' if d.is_dir() else 'MISS'} {d}")

    reference = load_reference(Path(args.reference))
    trial_votes = collect_trial_votes(run_dirs, args.trials, DOMAINS)
    summary = summarize_domain_votes(trial_votes, reference)

    print("\n=== Per-domain voted agreement + instability ===")
    print(f"{'Dom':<5}{'voted-agree%':>13}{'k3-base%':>10}{'delta':>8}{'unstable%':>11}")
    for dom in DOMAINS:
        s = summary[dom]
        base = K3_BASELINE[dom]
        delta = s.agreement_rate - base
        print(
            f"{dom:<5}{s.agreement_rate:>12.1f}%{base:>9}%{delta:>+8.1f}"
            f"{s.instability_rate:>10.1f}%"
        )
    print(
        "  NOTE: k3-base% is the MEAN per-run agreement across 3 runs (legacy "
        "metric); voted-agree% is the agreement of the majority-voted label."
    )

    print("\n=== Per-trial x domain instability map ===")
    print("  votes shown as {label: count}; * = unstable (no >=majority); "
          "x = voted label disagrees with reference")
    for trial in args.trials:
        gold = reference.get(trial, {})
        cells = []
        for dom in DOMAINS:
            vote = trial_votes[trial][dom]
            g = gold.get(dom)
            agree = (
                vote.judgement is not None
                and g is not None
                and _normalize(vote.judgement) == _normalize(g)
            )
            tag = ("" if vote.stable else "*") + ("" if agree else "x")
            dist = ",".join(f"{lbl}:{c}" for lbl, c in vote.vote_counts.items())
            miss = f"+{vote.missing_runs}miss" if vote.missing_runs else ""
            cells.append(f"{dom}={vote.judgement}{tag} [{dist}{miss}] (ref {g})")
        print(f"  {trial:<10} " + " | ".join(cells))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
