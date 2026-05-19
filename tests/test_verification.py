from rob2_pipeline.models import empty_paper_evidence
from rob2_pipeline.nodes.verification import (
    quote_is_supported,
    quote_verifier_node,
    verify_sq_evidence,
)


def test_quote_support_accepts_exact_source_quote():
    source = "Participants were randomly assigned using a central web system."

    assert quote_is_supported(
        '"Participants were randomly assigned"', source.casefold()
    )


def test_quote_support_rejects_hallucinated_quote():
    source = "Participants were randomly assigned using a central web system."

    assert not quote_is_supported(
        "Outcome assessors were blinded by an independent committee.", source.casefold()
    )


def test_verify_sq_evidence_flags_missing_d3_denominator():
    evidence = empty_paper_evidence()
    evidence["results"]["text"] = "Most participants had outcome data."
    state = {
        "full_text": "Most participants had outcome data.",
        "evidence": evidence,
        "rag_contexts": {},
        "sq_answers": {
            "3.1": {
                "answer": "Y",
                "quote": "Most participants had outcome data.",
                "justification": "Outcome data were nearly complete.",
            }
        },
    }

    flags = verify_sq_evidence(state)

    assert any(
        flag["sq_id"] == "3.1" and "denominator" in flag["issue"] for flag in flags
    )


def test_verify_sq_evidence_flags_unsupported_selective_reporting_quote():
    evidence = empty_paper_evidence()
    evidence["results"]["text"] = "The registered primary outcome was reported."
    state = {
        "full_text": "The registered primary outcome was reported.",
        "evidence": evidence,
        "rag_contexts": {},
        "sq_answers": {
            "5.2": {
                "answer": "PY",
                "quote": "Several unreported outcome scales were selectively omitted.",
                "justification": "The result appears selective.",
            }
        },
    }

    flags = verify_sq_evidence(state)

    assert any(flag["issue"] == "quote_not_found_in_source_context" for flag in flags)
    assert any("multiple eligible" in flag["issue"] for flag in flags)


def test_quote_verifier_surfaces_packet_retry_actions():
    state = {
        "full_text": "Progression-free survival improved.",
        "evidence": empty_paper_evidence(),
        "rag_contexts": {},
        "sq_answers": {},
        "evidence_packets": {
            "5.1": {
                "sq_id": "5.1",
                "packet_grade": {
                    "relevance": 0.1,
                    "coverage": 0.0,
                    "missing_evidence": ["protocol_or_registration"],
                    "retry_recommended": True,
                },
                "negative_flags": ["results_without_prespecification"],
            }
        },
        "verifier_trace": [],
    }

    result = quote_verifier_node(state)

    assert result["verification_actions"]
    assert result["verification_actions"][0]["sq_id"] == "5.1"
    assert result["verification_actions"][0]["action"] == "retry_packet_or_escalate"
    assert any(
        flag["sq_id"] == "5.1" and "packet" in flag["issue"]
        for flag in result["evidence_validation_flags"]
    )
