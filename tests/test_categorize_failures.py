import csv
import json
from pathlib import Path

from analysis.categorize_failures import (
    categorize_run,
    chunks_for_domain,
    heuristic_classify,
    l2_squared_to_cosine,
    llm_calls_for_domain,
    load_reference_csv,
    looks_ungrounded,
    write_summary_csv,
)


def _make_chunk(text: str, score: float, section: str = "Methods", pages=(1,)) -> dict:
    return {"text": text, "score": score, "section": section, "page_numbers": list(pages)}


def _make_llm_call(node: str, response: str) -> dict:
    return {
        "node": node,
        "system_prompt": "sys",
        "user_prompt": "user",
        "response": response,
        "model": "test",
        "input_tokens": 1,
        "output_tokens": 1,
        "cached": False,
        "latency_ms": 1,
        "cache_hit": False,
    }


def test_chunks_for_domain_reads_from_rag_sources():
    data = {
        "rag_sources": {
            "d1": [_make_chunk("randomization detail", 0.7)],
            "d2": [_make_chunk("blinding detail", 0.6)],
        }
    }
    d1_chunks = chunks_for_domain(data, "D1")
    assert len(d1_chunks) == 1
    assert d1_chunks[0]["text"] == "randomization detail"

    d2_chunks = chunks_for_domain(data, "D2")
    assert d2_chunks[0]["text"] == "blinding detail"

    d3_chunks = chunks_for_domain(data, "D3")
    assert d3_chunks == []


def test_llm_calls_for_domain_filters_by_node_prefix():
    trace = {
        "llm_calls": [
            _make_llm_call("domain1_sq11", "ans1"),
            _make_llm_call("domain2_sq21", "ans2"),
            _make_llm_call("domain1_sq12", "ans3"),
            _make_llm_call("rct_screener", "ans4"),
        ]
    }
    d1_calls = llm_calls_for_domain(trace, "D1")
    assert [c["node"] for c in d1_calls] == ["domain1_sq11", "domain1_sq12"]


def test_heuristic_classify_rag_miss_on_low_similarity():
    # FAISS returns L2 squared distance: score=1.7 -> cos = 1 - 1.7/2 = 0.15
    chunks = [_make_chunk("irrelevant", 1.7)]
    calls = [_make_llm_call("domain3_sq31", "confident answer")]
    cls, evidence = heuristic_classify(chunks, calls)
    assert cls == "rag_likely_miss"
    assert evidence["max_similarity_score"] == 0.15


def test_heuristic_classify_rag_miss_when_llm_signals_no_evidence():
    chunks = [_make_chunk("decent chunk", 0.7)]
    calls = [_make_llm_call("domain2_sq21", "No evidence of blinding details.")]
    cls, evidence = heuristic_classify(chunks, calls)
    assert cls == "rag_likely_miss"
    assert evidence["llm_signaled_no_evidence"] is True


def test_heuristic_classify_llm_miss_when_chunks_strong():
    chunks = [
        _make_chunk("chunk A " * 10, 0.7),
        _make_chunk("chunk B " * 10, 0.65),
        _make_chunk("chunk C " * 10, 0.55),
    ]
    response = "chunk A chunk A chunk A chunk A chunk A response with overlap"
    calls = [_make_llm_call("domain4_sq43", response)]
    cls, evidence = heuristic_classify(chunks, calls)
    assert cls == "llm_likely_miss"
    assert evidence["looks_ungrounded"] is False


def test_heuristic_classify_llm_miss_flags_ungrounded_response():
    chunks = [
        _make_chunk("ECOG performance status was 0 to 1 for all patients", 0.7),
        _make_chunk("Randomization was 1:1 stratified by disease volume", 0.6),
        _make_chunk("All-cause mortality served as the primary endpoint", 0.55),
    ]
    response = (
        "The assessment of clinical progression is inherently subjective and "
        "could be influenced by knowledge of intervention assignment in an "
        "open-label design."
    )
    calls = [_make_llm_call("domain4_sq45", response)]
    cls, evidence = heuristic_classify(chunks, calls)
    assert cls == "llm_likely_miss"
    assert evidence["looks_ungrounded"] is True


def test_heuristic_classify_ambiguous_mid_range():
    # L2 squared = 1.2 -> cos = 0.4 (>= 0.3 so not rag_miss, < 0.5 so not llm_miss)
    chunks = [_make_chunk("text", 1.2)]
    calls = [_make_llm_call("domain1_sq11", "some answer")]
    cls, _ = heuristic_classify(chunks, calls)
    assert cls == "ambiguous"


def test_l2_squared_to_cosine_inverts_distance_correctly():
    # For normalized embeddings: cos = 1 - L2squared/2; range [0, 1] clamped
    assert l2_squared_to_cosine(0.0) == 1.0  # identical vectors
    assert l2_squared_to_cosine(1.0) == 0.5  # midway
    assert l2_squared_to_cosine(2.0) == 0.0  # orthogonal
    assert l2_squared_to_cosine(3.0) == 0.0  # anti-aligned, clamped
    assert l2_squared_to_cosine(0.65) == 0.675  # representative live value


def test_heuristic_classify_does_not_invert_when_chunks_are_close():
    # Critical regression test for the L2 vs cosine bug. With L2 squared scoring,
    # low scores indicate STRONG retrieval, not weak. Pre-fix code would have
    # called this rag_likely_miss (score < 0.3); post-fix should be llm_likely_miss
    # because the cosine similarity is very high (~0.85+).
    chunks = [
        _make_chunk("chunk text " * 10, 0.25),
        _make_chunk("chunk text " * 10, 0.3),
        _make_chunk("chunk text " * 10, 0.35),
    ]
    calls = [_make_llm_call("domain1_sq11", "model said something not in chunks at all")]
    cls, evidence = heuristic_classify(chunks, calls)
    assert cls == "llm_likely_miss"
    assert evidence["max_similarity_score"] >= 0.8
    assert evidence["looks_ungrounded"] is True


def test_heuristic_classify_no_data():
    cls, evidence = heuristic_classify([], [])
    assert cls == "no_data"
    assert "no RAG retrieval" in evidence["reason"]


def test_looks_ungrounded_false_when_overlap_exists():
    chunks = [_make_chunk("the eligible age range was 18 to 70 years inclusive", 0.7)]
    response = "Per the methods, the eligible age range was 18 to 70 years inclusive."
    assert looks_ungrounded(response, chunks) is False


def test_looks_ungrounded_true_when_no_overlap():
    chunks = [_make_chunk("Patients were randomly assigned 1:1 to docetaxel.", 0.7)]
    response = "This subjective endpoint may be biased by open-label assessment."
    assert looks_ungrounded(response, chunks) is True


def test_looks_ungrounded_false_with_empty_inputs():
    assert looks_ungrounded("", [_make_chunk("text", 0.5)]) is False
    assert looks_ungrounded("response", []) is False


def test_categorize_run_emits_one_row_per_domain(tmp_path: Path):
    ref_csv = tmp_path / "overall_survival.csv"
    ref_csv.write_text(
        "Trial,D1,D2,D3,D4,D5,Overall Risk\n"
        "CHAARTED,L,L,L,L,L,Low\n",
        encoding="utf-8",
    )
    run = {
        "trace": {
            "trial": "CHAARTED",
            "outcome": "Overall Survival",
            "llm_calls": [_make_llm_call("domain4_sq43", "irrelevant generic answer")],
        },
        "data": {
            "domain_judgments": {"D1": "Low", "D2": "Low", "D3": "Low", "D4": "High", "D5": "Low"},
            "rag_sources": {
                "d1": [_make_chunk("randomization", 0.6)],
                "d2": [_make_chunk("blinding", 0.6)],
                "d3": [_make_chunk("missing data", 0.6)],
                "d4": [_make_chunk("outcome measurement", 0.55)],
                "d5": [_make_chunk("registration", 0.6)],
            },
        },
        "dir_name": "CHAARTED_os",
    }
    rows = categorize_run(run, {"OS": ref_csv})
    assert [r["domain"] for r in rows] == list(("D1", "D2", "D3", "D4", "D5"))
    matched_d4 = next(r for r in rows if r["domain"] == "D4")
    assert matched_d4["matched"] is False
    assert matched_d4["pipeline_judgment"] == "High"
    assert matched_d4["reference_judgment"] == "Low"
    assert matched_d4["classification"] in {"llm_likely_miss", "ambiguous"}
    matched_d1 = next(r for r in rows if r["domain"] == "D1")
    assert matched_d1["matched"] is True
    assert matched_d1["classification"] == "match"


def test_load_reference_csv_normalizes_judgments(tmp_path: Path):
    csv_path = tmp_path / "ref.csv"
    csv_path.write_text(
        "Trial,D1,D2,D3,D4,D5,Overall Risk\n"
        "TestTrial,L,S,H,L,L,Low\n",
        encoding="utf-8",
    )
    refs = load_reference_csv(csv_path)
    row = refs["testtrial"]
    assert row["D1"] == "Low"
    assert row["D2"] == "Some concerns"
    assert row["D3"] == "High"
    assert row["Overall"] == "Low"


def test_write_summary_csv_includes_looks_ungrounded(tmp_path: Path):
    rows = [{
        "trial": "X", "outcome_code": "OS", "domain": "D4",
        "pipeline_judgment": "High", "reference_judgment": "L", "matched": False,
        "classification": "llm_likely_miss",
        "max_similarity_score": 0.6, "avg_top3_similarity": 0.55,
        "n_chunks_retrieved": 3, "n_llm_calls": 1,
        "llm_signaled_no_evidence": False, "looks_ungrounded": True,
        "_chunks": [], "_llm_calls": [],
    }]
    out_csv = tmp_path / "out.csv"
    write_summary_csv(rows, out_csv)
    with out_csv.open() as f:
        reader = csv.DictReader(f)
        record = next(reader)
    assert record["looks_ungrounded"] == "True"
