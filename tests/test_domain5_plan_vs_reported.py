"""Regression: Domain 5 SQ 5.1 must prompt a pre-specified-plan-vs-reported-result
comparison on the LIVE JSON classifier path.

Background: for trials whose reported result came from an unplanned / data-driven
change to the analysis plan (a changed outcome or analysis timepoint, a follow-up or
analysis window extended after seeing the data, or post-hoc analyses added and then
selected for reporting), the weak benchmark model answered SQ 5.1 = ``Y`` merely because
a trial registration existed. It never compared the pre-specified plan against what was
actually reported. Under the Domain 5 judge, 5.1 = Y/PY with 5.2 = 5.3 = N/PN yields Low,
so the model under-called Some concerns.

The general Sterne 2019 Domain 5 principle (SQ 5.1, supplement p.26): the analysis should
follow a pre-specified plan finalized before unblinded outcome data; unexplained or
data-driven departures from that plan raise concern about selection of the reported
result. A PRE-SPECIFIED interim analysis (alpha-spending / group-sequential stopping
boundary) is part of the plan and is NOT such a departure.

On the JSON evidence-packet classifier path, only the per-code ``response_rules``
guidance reaches the model (``build_decision_table`` renders ``row["rule"]``; card
``notes`` are dropped). These tests lock that the plan-vs-reported principle and its
pre-specified-interim boundary are explicit in the 5.1 guidance the JSON path emits, so
the fix cannot regress by living only where the JSON path never surfaces it.
"""

from rob2_pipeline.nodes.evidence_contracts import CONTRACTS
from rob2_pipeline.nodes.evidence_packets import build_decision_table


def _json_path_rules(sq_id: str) -> dict[str, str]:
    """Answer-code -> rule text as the JSON evidence-packet classifier path renders it."""
    table = build_decision_table(
        contract=CONTRACTS[sq_id], facts=[], gaps=[], missing=[]
    )
    return {row["answer"]: row["rule"].lower() for row in table["rows"]}


def test_d5_sq51_prompts_plan_vs_reported_comparison_on_json_path():
    rules = _json_path_rules("5.1")

    # The "concern" side (PN) must describe an unplanned / data-driven departure from the
    # pre-specified plan as the trigger, with GENERAL examples (never trial-specific).
    pn = rules["PN"]
    assert "data-driven departure from the pre-specified plan" in pn
    # General example wording that covers an extended-after-seeing-data follow-up window
    # WITHOUT naming any trial's specific numbers.
    assert "after seeing the data" in pn
    assert "post-hoc" in pn

    # The "not a concern" side (Y) must instruct the plan-vs-reported comparison and
    # protect PRE-SPECIFIED interim analyses (alpha-spending), so pre-planned interims
    # stay Y/PY (e.g. TITAN) rather than being read as a departure.
    y = rules["Y"]
    assert "compare the pre-specified plan against what was reported" in y
    assert "pre-specified interim" in y
    assert "alpha-spending" in y


def test_d5_sq51_guidance_is_not_trial_specific():
    """Anti-overfit lock: the 5.1 guidance must not encode any benchmark trial's
    identifying facts (GETUG's 36-month follow-up / July 2011 cutoff)."""
    rules = _json_path_rules("5.1")
    joined = " ".join(rules.values())
    assert "36 month" not in joined
    assert "july 2011" not in joined
    assert "getug" not in joined
