from typing import NotRequired, TypedDict


class RoB2State(TypedDict):
    # === INPUT ===
    pdf_path: str
    full_text: str
    sections: dict[str, str]

    # === PRELIMINARY INFO ===
    is_rct: bool
    rct_screen_evidence: str
    intervention: str
    comparator: str
    outcome: str
    outcome_type: str
    numerical_result: str
    effect_of_interest: str
    registration_number: str
    n_randomized: str
    sources_consulted: list[str]

    # === SIGNALING QUESTION ANSWERS ===
    sq_answers: dict[str, dict]

    # === DOMAIN JUDGMENTS (set by deterministic nodes) ===
    domain_judgments: dict[str, str]
    domain_rationales: dict[str, str]

    # === OVERALL ===
    overall_judgment: str
    overall_rationale: str

    # === QUALITY FLAGS ===
    ni_count: int
    high_uncertainty_sqs: list[str]
    human_review_priority: str

    # === OUTPUT ===
    markdown_report: str
    json_output: dict

    # === METADATA ===
    errors: list[str]
    llm_call_log: list[dict]


RoB2State.__annotations__.pop("_RoB2State__debug_sections", None)
RoB2State.__annotations__["__debug_sections"] = NotRequired[dict]
