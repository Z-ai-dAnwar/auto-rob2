from typing import NotRequired, TypedDict


class LLMCallLogEntry(TypedDict):
    node: str
    prompt_length_chars: int
    response_length_chars: int
    latency_ms: int
    cache_hit: bool
    suspected_parse_failures: NotRequired[list[str]]
