from typing import NotRequired, TypedDict


class LLMCallLogEntry(TypedDict):
    node: str
    prompt_length_chars: int
    response_length_chars: int
    latency_ms: int
    cache_hit: bool
    model: NotRequired[str]
    input_tokens: NotRequired[int]
    output_tokens: NotRequired[int]
    cached: NotRequired[bool]
    parse_error: NotRequired[str]
    suspected_parse_failures: NotRequired[list[str]]
    chunk_sources: NotRequired[list[str]]


class ChunkMeta(TypedDict, total=False):
    text: str
    section: str
    page_numbers: list[int]
    score: float


class OutcomeProperties(TypedDict):
    objective_event: bool
    clinician_judged: bool
    patient_reported: bool
    composite: bool
    time_to_event: bool
    safety_harm: bool
    lab_or_imaging_threshold: bool
    blinded_adjudication: bool


class TrialFacts(TypedDict, total=False):
    randomization: str
    allocation_concealment: str
    masking: str
    protocol_deviations: str
    protocol_amendments: str
    analysis_populations: str
    source: str


class RetrievalGrade(TypedDict):
    relevance: float
    coverage: float
    missing_evidence: list[str]
    retry_recommended: bool


class EvidenceValidationFlag(TypedDict):
    sq_id: str
    issue: str
    quote: str


class VerifierTraceEntry(TypedDict, total=False):
    node: str
    sq_id: str
    action: str
    reason: str
    before: dict
    after: dict
