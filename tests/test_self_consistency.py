import json

from rob2_pipeline.self_consistency import (
    DomainVote,
    aggregate_domain,
    collect_trial_votes,
    summarize_domain_votes,
)


def test_clean_majority_three_of_five_is_stable():
    result = aggregate_domain(["Low", "Low", "Low", "Some concerns", "High"])
    assert result.judgement == "Low"
    assert result.stable is True


def test_two_two_one_tie_is_unstable_and_breaks_toward_more_cautious():
    # Low x2, Some concerns x2, High x1 -> no strict majority (need >=3 of 5).
    # The 2-2 tie is between Low and Some concerns; break toward the more
    # cautious of the tied labels -> Some concerns. Flagged unstable.
    result = aggregate_domain(["Low", "Low", "Some concerns", "Some concerns", "High"])
    assert result.stable is False
    assert result.judgement == "Some concerns"


def test_unanimous_is_stable_with_full_vote_counts():
    result = aggregate_domain(["Low", "Low", "Low", "Low", "Low"])
    assert result.judgement == "Low"
    assert result.stable is True
    assert result.vote_counts == {"Low": 5}
    assert result.missing_runs == 0


def test_single_missing_run_still_reaches_majority():
    # One run failed to score (None). Low still has 3 of 5 -> strict majority.
    result = aggregate_domain(["Low", "Low", "Low", "Some concerns", None])
    assert result.judgement == "Low"
    assert result.stable is True
    assert result.missing_runs == 1
    assert result.vote_counts == {"Low": 3, "Some concerns": 1}


def test_two_missing_runs_break_majority_into_unstable():
    # Two runs failed; the 3 present split 2-1 -> no >=3-of-5 majority.
    result = aggregate_domain(["Low", "Low", "Some concerns", None, None])
    assert result.stable is False
    assert result.missing_runs == 2
    assert result.judgement == "Low"


def test_casing_and_letter_codes_normalize_before_voting():
    # Mixed casing ("Some Concerns") and reference-style letter codes ("S")
    # must collapse to one label so they do not split the vote.
    result = aggregate_domain(["Some concerns", "Some Concerns", "S", "Low", "High"])
    assert result.judgement == "Some concerns"
    assert result.stable is True
    assert result.vote_counts == {"Some concerns": 3, "Low": 1, "High": 1}


def test_all_runs_missing_yields_no_judgement_flagged_unstable():
    # Every run failed to score: no label to report, definitively unstable.
    result = aggregate_domain([None, None, None, None, None])
    assert result.stable is False
    assert result.missing_runs == 5
    assert result.judgement is None
    assert result.vote_counts == {}


def _vote(judgement, stable):
    return DomainVote(judgement=judgement, stable=stable, vote_counts={}, missing_runs=0)


def test_summarize_counts_agreement_and_instability_independently():
    # Agreement (voted == reference) and instability (no strict majority) are
    # separate axes: T3 is unstable yet still agrees with the gold label.
    trial_votes = {
        "T1": {"D3": _vote("Low", True)},
        "T2": {"D3": _vote("High", True)},
        "T3": {"D3": _vote("Some concerns", False)},
    }
    reference = {
        "T1": {"D3": "L"},  # letter-code reference must normalize to match "Low"
        "T2": {"D3": "L"},
        "T3": {"D3": "S"},
    }
    summary = summarize_domain_votes(trial_votes, reference)
    assert summary["D3"].total == 3
    assert summary["D3"].agreements == 2  # T1 (Low==L) and T3 (Some concerns==S)
    assert summary["D3"].unstable == 1  # T3 only
    assert summary["D3"].agreement_rate == 200 / 3
    assert summary["D3"].instability_rate == 100 / 3


def _write_run(run_dir, trial, judgments):
    out = run_dir / f"{trial}_os"
    out.mkdir(parents=True)
    (out / f"{trial}_rob2_data.json").write_text(
        json.dumps({"domain_judgments": judgments})
    )


def test_collect_trial_votes_reads_run_dirs_and_tolerates_missing(tmp_path):
    run1 = tmp_path / "kvote_run1"
    run2 = tmp_path / "kvote_run2"
    run3 = tmp_path / "kvote_run3"  # whole run failed: no file written
    run3.mkdir()
    _write_run(run1, "T", {"D1": "Low", "D2": "High"})
    _write_run(run2, "T", {"D1": "Low"})  # D2 missing from this run

    votes = collect_trial_votes([run1, run2, run3], ["T"], ["D1", "D2"])

    # D1: [Low, Low, None] over k=3 -> majority Low, one missing run.
    assert votes["T"]["D1"].judgement == "Low"
    assert votes["T"]["D1"].stable is True
    assert votes["T"]["D1"].missing_runs == 1
    # D2: [High, None, None] over k=3 -> no majority, two missing runs.
    assert votes["T"]["D2"].judgement == "High"
    assert votes["T"]["D2"].stable is False
    assert votes["T"]["D2"].missing_runs == 2
