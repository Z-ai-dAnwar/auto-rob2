"""D2 SQ 2.6 must retrieve the analysis-population (ITT) statement.

D2's judgement hinges on SQ 2.6 ("was an appropriate analysis used to estimate
the effect of assignment to intervention?"). Answering it Y/N/NI requires the
sentence that names the analysis population the effect estimate came from
("efficacy analyses were by intention-to-treat" -> Y; a per-protocol / as-treated
analysis -> N/NI). That sentence is a single line; the generic 2.6 ranking terms
score it below denser deviation / adherence / population prose that matches more
terms, so it is crowded out of the top-3 and never reaches the model. On the same
paper the classifier then answers NI in some runs and Y in others (retrieval
variance, not reasoning variance).

This test pins that the analysis-population sentence must be selected into the
2.6 packet even when higher-ranking prose would otherwise take every slot. The
fix is a coverage group on CONTRACTS["2.6"] reserving one slot for the
analysis-population statement, honored by the existing _select_with_coverage.
This touches only source selection, never the judges or skip/NA logic.
"""

from rob2_pipeline.models import empty_paper_evidence
from rob2_pipeline.nodes.evidence_contracts import CONTRACTS
from rob2_pipeline.nodes.evidence_packets import build_packet_for_contract
from tests.test_evidence_packets import _RecordingSupplementIndex


# The deciding analysis-population sentence. It matches only one 2.6 ranking term
# ("intention"), so on matched-term count it loses the top-3 sort to the denser
# distractors below and is crowded out of the packet.
ANALYSIS_POPULATION_CHUNK = {
    "text": "Efficacy analyses were by intention-to-treat.",
    "section": "Statistical Analysis",
    "page_numbers": [2],
    "score": 0.40,
    "document_id": "primary:TRIAL",
    "document_name": "Primary report",
    "document_role": "primary",
    "source_kind": "rag_chunk",
    "source_path": "inputs/benchmark/TRIAL.pdf",
}


def _deviation_chunk(text: str, score: float, page: int) -> dict:
    # Deviation / adherence / population prose that each matches two or three of
    # SQ 2.6's ranking terms (randomized / modified / as treated), so it out-ranks
    # the single-term analysis-population sentence. None of these contain an
    # analysis-population coverage phrase, so only the ITT sentence can satisfy
    # the coverage group once it exists.
    return {
        "text": text,
        "section": "Results",
        "page_numbers": [page],
        "score": score,
        "document_id": "primary:TRIAL",
        "document_name": "Primary report",
        "document_role": "primary",
        "source_kind": "rag_chunk",
        "source_path": "inputs/benchmark/TRIAL.pdf",
    }


def _d2_state(chunks: list[dict]) -> dict:
    supplement_chunks = [
        {
            "source_kind": "supplement_segment",
            "document_id": chunk.get("document_id", "supplement:d2"),
            "document_name": chunk.get("document_name", "supplement.pdf"),
            "document_role": chunk.get("document_role", "primary"),
            "source_path": chunk.get("source_path", "supplement.pdf"),
            **chunk,
        }
        for chunk in chunks
    ]
    return {
        "outcome": "Overall Survival",
        "evidence": empty_paper_evidence("test"),
        "supplement_indexes": {
            "supplement:d2": _RecordingSupplementIndex(supplement_chunks)
        },
    }


def test_sq26_packet_selects_analysis_population_sentence_over_deviation_prose():
    state = _d2_state(
        [
            _deviation_chunk(
                "One patient was analysed as treated; the randomized and "
                "modified groups were otherwise balanced.",
                0.30,
                8,
            ),
            _deviation_chunk(
                "The randomized groups received a modified regimen schedule.",
                0.31,
                9,
            ),
            _deviation_chunk(
                "The randomized population received modified dosing; protocol "
                "deviations were rare.",
                0.32,
                10,
            ),
            ANALYSIS_POPULATION_CHUNK,
        ]
    )

    packet = build_packet_for_contract(state, CONTRACTS["2.6"])
    selected_text = " ".join(source.get("text", "") for source in packet["sources"])

    assert "intention-to-treat" in selected_text.casefold(), (
        "SQ 2.6 must select the analysis-population sentence ('efficacy analyses "
        "were by intention-to-treat') into its packet. With the current "
        "terms-only 2.6 contract that single-term sentence loses the top-3 sort "
        "to denser deviation / population prose and is crowded out, so 2.6 "
        "answers NI in some runs and Y in others on the same paper. A coverage "
        "group reserving one slot for the analysis-population statement fixes it."
    )
