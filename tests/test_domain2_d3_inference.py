from rob2_pipeline.nodes.evidence_contracts import CONTRACTS
from rob2_pipeline.nodes.evidence_packets import build_decision_table


def _json_path_rules(sq_id: str) -> dict[str, str]:
    """answer_code -> rule_text as the classifier sees it in the JSON decision table."""
    table = build_decision_table(contract=CONTRACTS[sq_id], facts=[], gaps=[], missing=[])
    return {row["answer"]: row["rule"].lower() for row in table["rows"]}


def test_d2_sq26_guidance_allows_itt_inference_without_literal_phrase():
    rules = _json_path_rules("2.6")
    combined_pos = rules["Y"] + " " + rules["PY"]
    assert "analysed in their assigned" in combined_pos or "all randomized" in combined_pos
    assert "literal" in combined_pos or "even if" in combined_pos
    assert "cannot be inferred" in rules["NI"] or "not be inferred" in rules["NI"]


def test_d2_sq26_still_calls_n_for_per_protocol():
    rules = _json_path_rules("2.6")
    assert "per-protocol" in rules["N"] or "as-treated" in rules["N"] or "as treated" in rules["N"]
