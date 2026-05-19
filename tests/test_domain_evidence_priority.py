from rob2_pipeline.models import empty_paper_evidence
from rob2_pipeline.nodes.domain1 import domain1_sq_node


def test_domain1_keeps_structured_evidence_when_rag_context_exists(monkeypatch):
    captured = {}

    def fake_call_node_llm(state, prompt, node_name, parse_fn, parse_sq_ids):
        captured["prompt"] = prompt
        parsed = {
            "1.1": {
                "answer": "Y",
                "quote": "central",
                "justification": "random",
                "uncertainty_flag": "NORMAL",
            },
            "1.2": {
                "answer": "Y",
                "quote": "central",
                "justification": "concealed",
                "uncertainty_flag": "NORMAL",
            },
            "1.3": {
                "answer": "N",
                "quote": "balanced",
                "justification": "balanced",
                "uncertainty_flag": "NORMAL",
            },
        }
        return "", [], parsed

    monkeypatch.setattr(
        "rob2_pipeline.nodes.domain_helpers.call_node_llm", fake_call_node_llm
    )
    evidence = empty_paper_evidence()
    evidence["d1_randomization"]["text"] = (
        "Allocation managed by the ECOG-ACRIN Statistical Center."
    )
    evidence["baseline_table"]["text"] = "Baseline characteristics were well balanced."
    evidence["consort_flow"]["text"] = "All randomized patients were included."
    state = {
        "intervention": "Docetaxel + ADT",
        "comparator": "ADT alone",
        "outcome": "Overall Survival",
        "evidence": evidence,
        "rag_contexts": {
            "d1": "Patients were assigned to ADT alone or ADT plus docetaxel."
        },
        "evidence_packets": {
            "1.1": {
                "domain": "d1",
                "required_evidence": ["sequence_generation"],
                "missing_evidence": [],
                "negative_flags": [],
                "sources": [],
            }
        },
        "sq_answers": {},
    }

    domain1_sq_node(state)

    assert (
        "Allocation managed by the ECOG-ACRIN Statistical Center" in captured["prompt"]
    )
    assert "Baseline characteristics were well balanced" in captured["prompt"]
    assert "Patients were assigned to ADT alone" in captured["prompt"]
    assert (
        "SQ 1.1" not in captured["prompt"]
        or "verified evidence packet" in captured["prompt"]
    )
