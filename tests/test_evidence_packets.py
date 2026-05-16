from rob2_pipeline.models import empty_paper_evidence
from rob2_pipeline.nodes.evidence_packets import build_evidence_packets, packet_block_for_domain


def _state_with_chunks(domain: str, chunks: list[dict], outcome: str = "Progression-Free Survival") -> dict:
    evidence = empty_paper_evidence("test")
    return {
        "outcome": outcome,
        "evidence": evidence,
        "rag_chunk_metadata": {
            "d1": [],
            "d2": [],
            "d3": [],
            "d4": [],
            "d5": [],
            domain: chunks,
        },
        "retrieval_grades": {},
    }


def test_builds_sq_specific_packet_for_allocation_concealment():
    state = _state_with_chunks(
        "d1",
        [
            {
                "text": "Allocation was concealed through a central web randomization system before enrolment.",
                "section": "Methods",
                "page_numbers": [3],
                "score": 0.1,
            }
        ],
    )

    result = build_evidence_packets(state)

    packet = result["evidence_packets"]["1.2"]
    assert packet["domain"] == "d1"
    assert "conceal" not in packet["missing_evidence"]
    assert packet["sources"][0]["page_numbers"] == [3]
    assert packet["retrieval_confidence"] > 0


def test_d3_completeness_packet_flags_missing_denominator():
    state = _state_with_chunks(
        "d3",
        [
            {
                "text": "The analysis used available participants and reported missing outcome data were uncommon.",
                "section": "Results",
                "page_numbers": [8],
                "score": 0.2,
            }
        ],
    )

    result = build_evidence_packets(state)

    packet = result["evidence_packets"]["3.1"]
    assert "denominator_or_percentage" in packet["missing_evidence"]
    assert packet["packet_grade"]["retry_recommended"] is True


def test_packet_builder_flags_wrong_outcome_context():
    state = _state_with_chunks(
        "d5",
        [
            {
                "text": "Overall survival was the primary endpoint and HR 0.82 was reported.",
                "section": "Results",
                "page_numbers": [9],
                "score": 0.1,
            }
        ],
        outcome="Progression-Free Survival",
    )

    result = build_evidence_packets(state)

    packet = result["evidence_packets"]["5.2"]
    assert "possible_wrong_outcome_context" in packet["negative_flags"]
    assert packet["packet_grade"]["retry_recommended"] is True


def test_d5_packet_flags_results_without_prespecification_evidence():
    state = _state_with_chunks(
        "d5",
        [
            {
                "text": "Progression-free survival improved with HR 0.70 and p=0.01.",
                "section": "Results",
                "page_numbers": [10],
                "score": 0.1,
            }
        ],
        outcome="Progression-Free Survival",
    )

    result = build_evidence_packets(state)

    packet = result["evidence_packets"]["5.1"]
    assert "results_without_prespecification" in packet["negative_flags"]
    assert "protocol_or_registration" in packet["missing_evidence"]


def test_packet_block_for_domain_is_compact_and_sq_labeled():
    state = _state_with_chunks(
        "d1",
        [
            {
                "text": "Participants were randomized using permuted blocks and allocation was concealed centrally.",
                "section": "Methods",
                "page_numbers": [2],
                "score": 0.1,
            }
        ],
    )
    result = build_evidence_packets(state)

    block = packet_block_for_domain(result["evidence_packets"], "d1")

    assert "SQ 1.1" in block
    assert "SQ 1.2" in block
    assert "page 2" in block
