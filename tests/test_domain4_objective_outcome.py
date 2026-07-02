"""Regression: Domain 4 objective-outcome steer must reach the model on the LIVE path.

Background (WS3): STAMPEDE D4 (ref Low, overall survival) voted LLHHL. The two High
runs answered SQ 4.2=Y (outcome measurement/ascertainment could differ between groups)
on ~identical evidence packets, while the Low runs answered 4.2=N/PN. The D4 judge maps
4.2=Y/PY -> High directly, so a stray Y flips the whole domain to High. This is reasoning
variance, not retrieval variance.

For objective outcomes such as all-cause mortality / overall survival, ascertainment of
the event (death) is objective and cannot be influenced by knowledge of assignment
(Sterne 2019 RoB 2, Domain 4). The existing objective-outcome nuance lived only in the
D4 card's ``notes``/``algorithm_note``. The JSON evidence-packet classifier path
(``build_decision_table``) renders ONLY the per-code ``response_rules`` guidance, so on
the live path the model never saw that nuance. These tests lock that the objective-outcome
steer is explicit in the ``response_rules`` guidance for SQ 4.2/4.3, so it reaches the
live classifier and cannot silently regress back into the dropped notes.
"""

from rob2_pipeline.methodology import DOMAIN4_METHODOLOGY
from rob2_pipeline.methodology.render import render_methodology
from rob2_pipeline.nodes.evidence_contracts import CONTRACTS
from rob2_pipeline.nodes.evidence_packets import build_decision_table


def _json_path_rules(sq_id: str) -> dict[str, str]:
    """Answer-code -> rule text as the JSON evidence-packet classifier path renders it."""
    table = build_decision_table(
        contract=CONTRACTS[sq_id], facts=[], gaps=[], missing=[]
    )
    return {row["answer"]: row["rule"] for row in table["rows"]}


def test_d4_sq42_objective_outcome_steer_reaches_live_decision_table():
    json_rules = _json_path_rules("4.2")

    # The objective-outcome steer must appear in the emitted N guidance (the target
    # answer), because that is the only 4.2 channel the live JSON classifier sees.
    n_rule = json_rules["N"].lower()
    assert "objective outcome" in n_rule
    assert "all-cause mortality" in n_rule
    assert "overall survival" in n_rule
    assert "sterne 2019" in n_rule

    # Anti-overfit guard: the steer applies ONLY to genuinely objective outcomes; it
    # must NOT bias D4 toward Low for subjective / assessor-judged outcomes.
    assert "subjective" in n_rule

    # Raise the bar for the High-driving Y answer: differential ascertainment for an
    # objective mortality endpoint needs specific evidence, not routine visit-frequency
    # differences.
    y_rule = json_rules["Y"].lower()
    assert "objective" in y_rule
    assert "differential ascertainment" in y_rule


def test_d4_sq43_objective_outcome_note_reaches_live_decision_table():
    json_rules = _json_path_rules("4.3")
    n_rule = json_rules["N"].lower()
    assert "objective outcome" in n_rule
    assert "all-cause mortality" in n_rule
    assert "sterne 2019" in n_rule


def test_d4_objective_outcome_steer_also_present_on_xml_render_path():
    # The XML prompt path renders both notes and guidance; the steer being in guidance
    # means it now surfaces on BOTH channels, never only in the dropped notes.
    xml = render_methodology(DOMAIN4_METHODOLOGY, ["4.1", "4.2", "4.3"]).lower()
    assert "objective outcome" in xml
    assert "all-cause mortality" in xml
    assert "overall survival" in xml
