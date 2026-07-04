"""Deterministic acceptance test for ADR-0008 primary-paper BM25 retrieval.

Pilot scope: D2 SQ 2.6 (analysis-population). This test runs on REAL data, not a
synthetic fixture (a synthetic candidate was the failure mode of the reverted
prior attempt): tests/fixtures/getug_afu15_primary_paper.json holds GETUG-AFU-15's
real parsed ``full_text`` and the real (incomplete) ``paper_evidence_extraction``
LLM summary, both taken verbatim from a baseline trace
(outputs/benchmark/kvote_mt8k1/GETUG-AFU-15_os/GETUG-AFU-15_trace.json).

The decisive sentence "Efficacy analyses were done by intention to treat" is in
the paper, but the stochastic LLM summary dropped it from 2.6's fallback sections
(results / d4_outcome_meas / methods). Deterministic BM25 over ``full_text`` must
surface it into the 2.6 packet.

Determinism note: ``full_text`` and BM25 are both deterministic, so a passage that
is present once here is present on every run. "Present once == present every run",
which is the whole point of moving this evidence off the stochastic summary.
"""

import json
from pathlib import Path

import pytest

from rob2_pipeline.nodes.evidence_contracts import CONTRACTS
from rob2_pipeline.nodes.evidence_packets import build_packet_for_contract
from rob2_pipeline.nodes.evidence_source_selection import (
    candidate_sources,
    fallback_sources,
)
from rob2_pipeline.primary_paper_index import build_primary_index

ITT_SENTENCE = "intention to treat"
FIXTURE = Path(__file__).parent / "fixtures" / "getug_afu15_primary_paper.json"


def _contains_itt(texts) -> bool:
    return any(ITT_SENTENCE in str(text).lower() for text in texts)


@pytest.fixture
def getug_state() -> dict:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    full_text = data["full_text"]
    return {
        "full_text": full_text,
        "evidence": data["evidence"],
        "pdf_path": "GETUG-AFU-15.pdf",
        # Built once per trial in ingestion; supplied here directly from the real
        # full_text so the test does not depend on the ingestion/parse pipeline.
        "primary_index": build_primary_index(full_text),
    }


def test_llm_summary_fallback_drops_itt_sentence_for_d2_26(getug_state):
    """Documents the failure mode: the stochastic summary that feeds 2.6's
    fallback sections does not carry the ITT sentence in this real trace."""
    fallback = fallback_sources(getug_state, CONTRACTS["2.6"])

    assert not _contains_itt(source["text"] for source in fallback)


def test_primary_retrieval_surfaces_itt_sentence_in_candidates(getug_state):
    """RED before ADR-0008 (no deterministic primary-paper producer), GREEN
    after: the ITT sentence reaches the 2.6 candidate sources via BM25."""
    sources = candidate_sources(getug_state, CONTRACTS["2.6"])

    itt_sources = [s for s in sources if ITT_SENTENCE in s["text"].lower()]
    assert itt_sources, "primary-paper BM25 retrieval must surface the ITT sentence"
    assert any(s["source_kind"] == "primary_fulltext" for s in itt_sources)


def test_itt_sentence_reaches_the_2_6_packet(getug_state):
    """The decisive sentence must survive ranking/selection into the packet, not
    just appear among candidates."""
    packet = build_packet_for_contract(getug_state, CONTRACTS["2.6"])

    assert ITT_SENTENCE in packet["text"].lower()
    assert _contains_itt(source["text"] for source in packet["sources"])


def test_primary_retrieval_is_deterministic(getug_state):
    """full_text + BM25 are deterministic, so the packet is byte-identical across
    builds: present-once implies present-every-run."""
    first = build_packet_for_contract(getug_state, CONTRACTS["2.6"])
    second = build_packet_for_contract(getug_state, CONTRACTS["2.6"])

    assert first["text"] == second["text"]
    assert ITT_SENTENCE in first["text"].lower()


def test_primary_retrieval_gated_off_for_non_pilot_sq(getug_state):
    """Pilot scope is 2.6 only. A non-pilot SQ (2.1) must get no primary_fulltext
    sources, so other domains' packets are untouched by the pilot."""
    sources = candidate_sources(getug_state, CONTRACTS["2.1"])

    assert not any(s["source_kind"] == "primary_fulltext" for s in sources)
