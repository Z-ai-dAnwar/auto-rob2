"""Tests for per-signalling-question RAG query coverage."""

from rob2_pipeline.rag_queries import SQ_QUERIES, domain_queries


def test_sq_queries_has_all_domains():
    sq_ids = set(SQ_QUERIES.keys())

    assert {"1.1", "1.2", "1.3"}.issubset(sq_ids)
    assert {"2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7"}.issubset(sq_ids)
    assert {"3.1", "3.2", "3.3", "3.4"}.issubset(sq_ids)
    assert {"4.1", "4.2", "4.3", "4.4", "4.5"}.issubset(sq_ids)
    assert {"5.1", "5.2", "5.3"}.issubset(sq_ids)


def test_sq_queries_each_sq_has_at_least_three_queries():
    for sq_id, queries in SQ_QUERIES.items():
        assert len(queries) >= 3, f"SQ {sq_id} has only {len(queries)} queries"


def test_domain_queries_d1_returns_sq1_queries_and_stays_outcome_agnostic():
    queries = domain_queries("d1")
    expected = SQ_QUERIES["1.1"] + SQ_QUERIES["1.2"] + SQ_QUERIES["1.3"]
    joined = " ".join(queries).lower()

    assert set(queries) == set(expected)
    assert "outcome" not in joined
    assert "overall survival" not in joined
    assert "progression-free survival" not in joined
    assert "adverse events" not in joined


def test_domain_queries_d2_returns_sq2_queries():
    queries = domain_queries("d2")
    expected = []
    for sq_id in ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7"]:
        expected.extend(SQ_QUERIES[sq_id])

    assert set(queries) == set(expected)


def test_domain_queries_d5_returns_sq5_queries_and_sap_terms():
    queries = domain_queries("d5")
    expected = SQ_QUERIES["5.1"] + SQ_QUERIES["5.2"] + SQ_QUERIES["5.3"]
    joined = " ".join(queries).lower()

    assert set(queries) == set(expected)
    assert "statistical analysis plan" in joined
    assert "pre-specified" in joined


def test_domain_queries_returns_list_of_strings():
    for domain in ["d1", "d2", "d3", "d4", "d5"]:
        queries = domain_queries(domain)
        assert isinstance(queries, list)
        assert all(isinstance(q, str) for q in queries)
        assert len(queries) > 0
