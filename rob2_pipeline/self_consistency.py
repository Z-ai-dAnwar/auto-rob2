"""Self-consistency (k-vote) aggregation for RoB 2 domain judgements.

Outer aggregation layer only: this module takes the per-run domain judgements
produced by k repeated assessments of the same trial and returns one voted
judgement per domain plus an instability signal. It does NOT touch the per-run
pipeline, the deterministic judges, the skip/NA logic, or the RoB 2 algorithm.
"""

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

# Ascending caution. Matches benchmark.py's JUDGMENT_ORDER: when the k runs do
# not reach a strict majority, RoB 2 is a risk instrument, so the reported label
# breaks toward the more cautious judgement.
CAUTION_ORDER = ("Low", "Some concerns", "High")

# Collapse the casing drift and reference-style letter codes (L/S/H) seen across
# run outputs onto the canonical labels, so equivalent judgements do not split
# the vote. Kept in sync by hand with benchmark.py's _normalize_judgment (this is
# a superset of its mapping).
_CANONICAL = {
    "l": "Low",
    "low": "Low",
    "low risk": "Low",
    "s": "Some concerns",
    "some concerns": "Some concerns",
    "some-concerns": "Some concerns",
    "h": "High",
    "high": "High",
    "high risk": "High",
}


@dataclass
class DomainVote:
    judgement: str | None
    stable: bool
    vote_counts: dict[str, int]
    missing_runs: int


def _normalize(label: str) -> str:
    # Collapse internal whitespace runs (not just outer strip) before lookup, so
    # this matches benchmark.py's _normalize_judgment behaviour rather than only
    # approximating it.
    collapsed = " ".join(label.split())
    return _CANONICAL.get(collapsed.casefold(), collapsed)


def _caution_rank(label: str) -> int:
    # Unknown labels (drift that survived normalization) rank below every known
    # judgement, so a recognized canonical label always wins the tie-break and
    # the conservative pick never raises on an unexpected string.
    return CAUTION_ORDER.index(label) if label in CAUTION_ORDER else -1


def _load_domain_judgments(run_dir: Path, trial: str) -> dict[str, str]:
    # Each run writes {run_dir}/{trial}_os/{trial}_rob2_data.json. A run that
    # failed or was hard-killed mid-write leaves the file absent or truncated;
    # either way that is a missing vote, not a scorer crash.
    path = Path(run_dir) / f"{trial}_os" / f"{trial}_rob2_data.json"
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    judgments = data.get("domain_judgments", {})
    return judgments if isinstance(judgments, dict) else {}


def collect_trial_votes(
    run_dirs: list[Path],
    trials: list[str],
    domains: list[str],
) -> dict[str, dict[str, DomainVote]]:
    """Load the k run outputs and majority-vote each trial's domain judgements.

    For every (trial, domain) it gathers one label per run dir (None where the
    run or the domain is missing) and aggregates. Outer layer only: it reads the
    per-run JSON the pipeline already wrote and never re-runs an assessment.
    """
    votes: dict[str, dict[str, DomainVote]] = {}
    for trial in trials:
        per_run = [_load_domain_judgments(run_dir, trial) for run_dir in run_dirs]
        votes[trial] = {
            domain: aggregate_domain([judgments.get(domain) for judgments in per_run])
            for domain in domains
        }
    return votes


@dataclass
class DomainSummary:
    agreements: int
    unstable: int
    total: int

    @property
    def agreement_rate(self) -> float:
        return 100 * self.agreements / self.total if self.total else 0.0

    @property
    def instability_rate(self) -> float:
        return 100 * self.unstable / self.total if self.total else 0.0


def summarize_domain_votes(
    trial_votes: dict[str, dict[str, DomainVote]],
    reference: dict[str, dict[str, str]],
) -> dict[str, DomainSummary]:
    """Roll per-trial domain votes up into per-domain agreement + instability.

    Agreement compares the voted judgement to the (normalized) reference label;
    instability counts trials where the k runs reached no strict majority. The
    two are tracked independently: an unstable domain can still agree with gold.
    """
    agreements: Counter[str] = Counter()
    unstable: Counter[str] = Counter()
    total: Counter[str] = Counter()
    for trial, domain_votes in trial_votes.items():
        trial_reference = reference.get(trial, {})
        for domain, vote in domain_votes.items():
            total[domain] += 1
            if not vote.stable:
                unstable[domain] += 1
            gold = trial_reference.get(domain)
            if (
                vote.judgement is not None
                and gold is not None
                and _normalize(vote.judgement) == _normalize(gold)
            ):
                agreements[domain] += 1
    return {
        domain: DomainSummary(
            agreements=agreements[domain],
            unstable=unstable[domain],
            total=total[domain],
        )
        for domain in total
    }


def aggregate_domain(runs: list[str | None]) -> DomainVote:
    # A run that failed to score is represented as None. It counts toward the
    # intended k (the majority denominator) but not toward any label, so failures
    # make consensus harder to reach rather than being silently dropped.
    present = [_normalize(label) for label in runs if label is not None]
    missing_runs = len(runs) - len(present)
    if not present:
        # Every run failed: no label to report, definitively unstable.
        return DomainVote(
            judgement=None,
            stable=False,
            vote_counts={},
            missing_runs=missing_runs,
        )
    counts = Counter(present)
    threshold = len(runs) // 2 + 1
    top = max(counts.values())
    modal = [label for label, count in counts.items() if count == top]
    vote_counts = dict(counts)
    if top >= threshold:
        # A strict majority is necessarily unique for these k.
        return DomainVote(
            judgement=modal[0],
            stable=True,
            vote_counts=vote_counts,
            missing_runs=missing_runs,
        )
    # No strict majority: flag unstable and report the most cautious of the
    # labels tied for the top count.
    return DomainVote(
        judgement=max(modal, key=_caution_rank),
        stable=False,
        vote_counts=vote_counts,
        missing_runs=missing_runs,
    )
