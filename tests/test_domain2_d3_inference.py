from rob2_pipeline.nodes.evidence_contracts import CONTRACTS
from rob2_pipeline.nodes.evidence_packets import build_decision_table


def _json_path_rules(sq_id: str) -> dict[str, str]:
    """Answer-code -> rule text as the classifier sees it in the JSON decision table."""
    table = build_decision_table(contract=CONTRACTS[sq_id], facts=[], gaps=[], missing=[])
    return {row["answer"]: row["rule"] for row in table["rows"]}


def test_d2_sq26_guidance_allows_itt_inference_without_literal_phrase():
    rules = _json_path_rules("2.6")
    y, py = rules["Y"].lower(), rules["PY"].lower()
    assert any("analysed in their assigned" in t or "all randomized" in t for t in (y, py))
    assert "literal" in y or "even if" in y


def test_d2_sq26_ni_is_restricted_to_uninferable():
    rules = _json_path_rules("2.6")
    assert "cannot be inferred" in rules["NI"].lower()


def test_d2_sq26_still_calls_n_for_per_protocol():
    rules = _json_path_rules("2.6")
    n = rules["N"].lower()
    assert "per-protocol" in n or "as-treated" in n or "as treated" in n
