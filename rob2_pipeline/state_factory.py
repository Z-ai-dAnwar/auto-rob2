from rob2_pipeline.constants import DEFAULT_EFFECT_OF_INTEREST, NOT_REPORTED
from rob2_pipeline.models import empty_paper_evidence
from rob2_pipeline.state import RoB2State


def create_initial_state(
    pdf_path: str,
    outcome: str | None = None,
    effect_of_interest: str = DEFAULT_EFFECT_OF_INTEREST,
    **kwargs,
) -> RoB2State:
    return {
        "pdf_path": pdf_path,
        "full_text": "",
        "evidence": empty_paper_evidence(),
        "docling_doc": None,
        "docling_chunks": [],
        "rag_contexts": {},
        "rag_chunk_metadata": {},
        "is_rct": False,
        "rct_screen_evidence": "",
        "intervention": NOT_REPORTED,
        "comparator": NOT_REPORTED,
        "outcome": outcome or "",
        "outcome_type": "clinician-composite",
        "numerical_result": NOT_REPORTED,
        "effect_of_interest": effect_of_interest,
        "registration_number": NOT_REPORTED,
        "registered_endpoint": NOT_REPORTED,
        "registered_secondary_endpoints": kwargs.get("registered_secondary_endpoints", "Not reported"),
        "registered_analysis": NOT_REPORTED,
        "ctgov_outcomes": kwargs.get("ctgov_outcomes", "(ClinicalTrials.gov data not yet retrieved)"),
        "n_randomized": NOT_REPORTED,
        "sources_consulted": [],
        "sq_answers": {},
        "domain_judgments": {},
        "domain_rationales": {},
        "overall_judgment": "",
        "overall_rationale": "",
        "ni_count": 0,
        "high_uncertainty_sqs": [],
        "human_review_priority": "HIGH",
        "markdown_report": "",
        "errors": [],
        "llm_call_log": [],
    }
