from rob2_pipeline.models import empty_paper_evidence


def _evidence():
    evidence = empty_paper_evidence("fallback")
    evidence["d1_randomization"]["text"] = "Randomized centrally."
    evidence["d2_blinding"]["text"] = "Open-label trial."
    evidence["d3_missing_data"]["text"] = "Complete follow-up."
    evidence["d4_outcome_meas"]["text"] = "Overall survival endpoint."
    evidence["d5_registration"]["text"] = "NCT00000000."
    evidence["methods"]["text"] = "Intention-to-treat methods."
    evidence["results"]["text"] = "All randomized participants analysed."
    return evidence


def test_rag_retrieval_node_uses_fallback_evidence_when_docling_doc_absent():
    from rob2_pipeline.nodes.rag_retrieval import rag_retrieval_node
    from rob2_pipeline.rag_queries import DOMAIN_QUERIES

    result = rag_retrieval_node({"evidence": _evidence(), "full_text": "", "outcome": "Overall Survival"})

    assert set(result["rag_contexts"]) == set(DOMAIN_QUERIES)
    assert "Randomized centrally" in result["rag_contexts"]["d1"]
    assert "Open-label" in result["rag_contexts"]["d2_blinding"]
    assert "All randomized" in result["rag_contexts"]["d2_analysis"]
    assert "NCT00000000" in result["rag_contexts"]["d5"]


def test_rag_retrieval_node_builds_index_and_augments_d3(monkeypatch):
    import rob2_pipeline.nodes.rag_retrieval as node
    from rob2_pipeline.rag_queries import DOMAIN_QUERIES

    calls = []

    monkeypatch.setattr(node, "chunk_docling_doc", lambda conv_result: [{"text": "chunk", "section": "Methods", "idx": 0}])
    monkeypatch.setattr(node, "build_index", lambda chunks: ("index", chunks))

    def fake_retrieve(index, chunks, queries):
        calls.append((index, tuple(queries)))
        return "retrieved " + queries[0]

    monkeypatch.setattr(node, "retrieve", fake_retrieve)
    monkeypatch.setattr(node, "extract_censoring_context", lambda full_text, outcome: "415 events observed")

    result = node.rag_retrieval_node(
        {
            "docling_doc": object(),
            "evidence": _evidence(),
            "full_text": "At final analysis, 415 events were observed.",
            "outcome": "Overall Survival",
        }
    )

    assert set(result["rag_contexts"]) == set(DOMAIN_QUERIES)
    assert len(calls) == len(DOMAIN_QUERIES)
    assert "415 events observed" in result["rag_contexts"]["d3"]


def test_rag_retrieval_node_falls_back_when_rag_errors(monkeypatch):
    import rob2_pipeline.nodes.rag_retrieval as node

    def boom(_conv_result):
        raise RuntimeError("embedding init failed")

    monkeypatch.setattr(node, "chunk_docling_doc", boom)
    monkeypatch.setattr(node, "extract_censoring_context", lambda full_text, outcome: "")

    state = {
        "docling_doc": object(),
        "evidence": _evidence(),
        "full_text": "",
        "outcome": "Overall Survival",
    }
    result = node.rag_retrieval_node(state)

    assert "Randomized centrally" in result["rag_contexts"]["d1"]
    assert any("RAG retrieval failed" in warning for warning in state["evidence"]["warnings"])
