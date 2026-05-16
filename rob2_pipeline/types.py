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
