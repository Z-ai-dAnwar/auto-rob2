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


def test_unique_plurality_without_majority_reports_plurality_unstable():
    # k=4: Low is the unique top (2) but < 3, so no strict majority. There is no
    # tie to break, so the plurality (Low) is reported and flagged unstable. The
    # cautious lean applies only to actual ties on purpose: leaning cautious on
    # every unstable domain would bias agreement, since the references skew Low.
    result = aggregate_domain(["Low", "Low", "Some concerns", "High"])
    assert result.stable is False
    assert result.judgement == "Low"


def test_even_k_three_three_split_is_unstable_and_cautious():
    # k=6: a 3-3 tie between Low and High -> no >=4 majority -> unstable, and the
    # tie breaks toward the more cautious label (High).
    result = aggregate_domain(["Low", "Low", "Low", "High", "High", "High"])
    assert result.stable is False
    assert result.judgement == "High"


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


def test_tie_break_prefers_known_label_and_never_crashes_on_drift():
    # An unrecognized label must not crash the conservative tie-break; among the
    # labels tied for the top count a recognized canonical label is preferred.
    result = aggregate_domain(["moderate", "Low", "Low", "moderate", "High"])
    assert result.stable is False
    assert result.judgement == "Low"


def test_double_spaced_label_normalizes_like_benchmark():
    # Internal whitespace runs collapse (matches benchmark.py normalization), so
    # "Some  concerns" must not split the vote against "Some concerns"/"S".
    result = aggregate_domain(["Some  concerns", "Some concerns", "S", "Low", "High"])
    assert result.judgement == "Some concerns"
    assert result.stable is True
    assert result.vote_counts == {"Some concerns": 3, "Low": 1, "High": 1}


def test_collect_tolerates_corrupt_json(tmp_path):
    # The watchdog hard-kills a stalled run, which can leave a truncated JSON
    # file. That is a missing vote, not a scorer crash.
    run1 = tmp_path / "kvote_run1"
    run2 = tmp_path / "kvote_run2"
    _write_run(run1, "T", {"D1": "Low"})
    bad = run2 / "T_os"
    bad.mkdir(parents=True)
    (bad / "T_rob2_data.json").write_text('{"domain_judgments": {"D1": "Lo')

    votes = collect_trial_votes([run1, run2], ["T"], ["D1"])

    assert votes["T"]["D1"].judgement == "Low"
    assert votes["T"]["D1"].missing_runs == 1


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
