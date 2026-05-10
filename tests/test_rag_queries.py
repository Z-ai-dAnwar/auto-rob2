"""Tests for domain-specific RAG query coverage."""


def test_d1_rag_queries_cover_key_concepts():
    from rob2_pipeline.rag_queries import DOMAIN_QUERIES

    d1 = " ".join(DOMAIN_QUERIES["d1"])

    assert "block" in d1.lower() or "stratif" in d1.lower()
    assert "central" in d1.lower()
    assert "minimi" in d1.lower()


def test_d5_rag_queries_cover_sap_concepts():
    from rob2_pipeline.rag_queries import DOMAIN_QUERIES

    d5 = " ".join(DOMAIN_QUERIES["d5"])

    assert "statistical analysis plan" in d5.lower()
    assert "pre-specified" in d5.lower()
