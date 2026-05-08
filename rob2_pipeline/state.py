import operator
from typing import Annotated, TypedDict

from rob2_pipeline.types import LLMCallLogEntry


def merge_dicts(left: dict, right: dict) -> dict:
    merged = dict(left or {})
    merged.update(right or {})
    return merged


def take_latest(_left, right):
    return right


class RoB2State(TypedDict):
    # === INPUT ===
    pdf_path: Annotated[str, take_latest]
    full_text: Annotated[str, take_latest]
    sections: Annotated[dict[str, str], take_latest]

    # === PRELIMINARY INFO ===
    is_rct: Annotated[bool, take_latest]
    rct_screen_evidence: Annotated[str, take_latest]
    intervention: Annotated[str, take_latest]
    comparator: Annotated[str, take_latest]
    outcome: Annotated[str, take_latest]
    outcome_type: Annotated[str, take_latest]
    numerical_result: Annotated[str, take_latest]
    effect_of_interest: Annotated[str, take_latest]
    registration_number: Annotated[str, take_latest]
    registered_endpoint: Annotated[str, take_latest]
    registered_analysis: Annotated[str, take_latest]
    n_randomized: Annotated[str, take_latest]
    sources_consulted: Annotated[list[str], take_latest]

    # === SIGNALING QUESTION ANSWERS ===
    sq_answers: Annotated[dict[str, dict], merge_dicts]

    # === DOMAIN JUDGMENTS (set by deterministic nodes) ===
    domain_judgments: Annotated[dict[str, str], merge_dicts]
    domain_rationales: Annotated[dict[str, str], merge_dicts]

    # === OVERALL ===
    overall_judgment: Annotated[str, take_latest]
    overall_rationale: Annotated[str, take_latest]

    # === QUALITY FLAGS ===
    ni_count: Annotated[int, take_latest]
    high_uncertainty_sqs: Annotated[list[str], take_latest]
    human_review_priority: Annotated[str, take_latest]

    # === OUTPUT ===
    markdown_report: Annotated[str, take_latest]

    # === METADATA ===
    errors: Annotated[list[str], take_latest]
    llm_call_log: Annotated[list[LLMCallLogEntry], operator.add]
