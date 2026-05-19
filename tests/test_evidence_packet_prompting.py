from rob2_pipeline.models import empty_paper_evidence
from rob2_pipeline.nodes.domain1 import domain1_sq_node


def test_domain_prompt_includes_verified_evidence_packet(monkeypatch):
    captured = {}
    evidence = empty_paper_evidence("test")
    evidence["d1_randomization"]["text"] = "Participants were randomized centrally."
    state = {
        "evidence": evidence,
        "intervention": "Drug A",
        "comparator": "Placebo",
        "outcome": "Overall Survival",
        "ctgov_design": "",
        "rag_contexts": {"d1": "generic randomization context"},
        "rag_chunk_metadata": {},
        "trial_facts": {},
        "sq_answers": {},
        "evidence_packets": {
            "1.1": {
                "sq_id": "1.1",
                "domain": "d1",
                "required_evidence": ["sequence_generation"],
                "missing_evidence": [],
                "negative_flags": [],
                "sources": [
                    {
                        "text": "Computer-generated random allocation sequence.",
                        "section": "Methods",
                        "page_numbers": [2],
                        "score": 0.1,
                    }
                ],
            }
        },
    }

    def fake_call(
        call_fn, state, prompt, node_name, parse_fn, parse_sq_ids, chunk_sources
    ):
        captured["prompt"] = prompt
        return (
            "",
            [],
            {
                "1.1": {
                    "answer": "Y",
                    "quote": "Computer-generated",
                    "justification": "Random sequence.",
                },
                "1.2": {
                    "answer": "NI",
                    "quote": "No relevant text found",
                    "justification": "Missing.",
                },
                "1.3": {
                    "answer": "NI",
                    "quote": "No relevant text found",
                    "justification": "Missing.",
                },
            },
        )

    monkeypatch.setattr(
        "rob2_pipeline.nodes.domain_helpers.call_node_llm_with_sources", fake_call
    )

    domain1_sq_node(state)

    assert "SQ 1.1 verified evidence packet" in captured["prompt"]
    assert "Computer-generated random allocation sequence" in captured["prompt"]
