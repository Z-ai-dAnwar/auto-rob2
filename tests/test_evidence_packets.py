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


def test_section_fallback_excluded_when_rag_returned_chunks():
    """When RAG has chunks for a domain, the candidate pool must contain no
    section-text fallback sources (which have empty page_numbers and a
    hardcoded score of 2.0 that would outrank real RAG hits)."""
    evidence = empty_paper_evidence("test")
    # Populate the section evidence that _fallback_sources would otherwise pull.
    # If the fallback runs, the test will see a source with empty page_numbers
    # and section="d1_randomization".
    evidence["d1_randomization"]["text"] = (
        "Patients were randomized 1:1 using a centralized interactive web response system."
    )
    state = {
        "outcome": "Overall Survival",
        "evidence": evidence,
        "rag_chunk_metadata": {
            "d1": [
                {
                    "text": "Randomization used permuted blocks stratified by site.",
                    "section": "Methods",
                    "page_numbers": [4],
                    "score": 0.5,
                }
            ],
            "d2": [],
            "d3": [],
            "d4": [],
            "d5": [],
        },
        "retrieval_grades": {},
    }

    result = build_evidence_packets(state)

    # SQs 1.1, 1.2, 1.3 all live in domain d1. None of their sources should
    # be section-text fallbacks now that RAG returned a chunk for d1.
    for sq_id in ("1.1", "1.2", "1.3"):
        sources = result["evidence_packets"][sq_id]["sources"]
        for source in sources:
            # Section-text fallbacks have empty page_numbers and a section
            # name that matches a PaperEvidence key like "d1_randomization".
            assert source["section"] not in {
                "d1_randomization",
                "baseline_table",
                "methods",
            }, (
                f"SQ {sq_id} picked up section-text fallback source "
                f"{source['section']!r} even though RAG returned chunks"
            )
            assert source["page_numbers"], (
                f"SQ {sq_id} has a source with empty page_numbers, which "
                f"means a section-text fallback leaked into the candidate pool"
            )


def test_section_fallback_used_when_rag_pool_is_empty():
    """When RAG returns no chunks for a domain, the section-text fallback
    must still fire so the packet has something to work with."""
    evidence = empty_paper_evidence("test")
    evidence["d1_randomization"]["text"] = (
        "Patients were randomly assigned 1:1 using a computer-generated sequence."
    )
    state = {
        "outcome": "Overall Survival",
        "evidence": evidence,
        # No RAG chunks for any domain. Fallback should fire for d1.
        "rag_chunk_metadata": {
            "d1": [],
            "d2": [],
            "d3": [],
            "d4": [],
            "d5": [],
        },
        "retrieval_grades": {},
    }

    result = build_evidence_packets(state)

    packet_1_1 = result["evidence_packets"]["1.1"]
    sources = packet_1_1["sources"]
    assert sources, (
        "SQ 1.1 should have section-text fallback sources when RAG pool is "
        "empty for d1"
    )
    # At least one source should be the section-text fallback.
    assert any(
        source["section"] == "d1_randomization" for source in sources
    ), "section-text fallback for d1_randomization should appear in sources"
