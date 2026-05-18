"""Per-run trace collector for diagnostic analysis (Option C: LLM I/O only).

Captures full LLM system/user prompts and responses so failures can be
categorized as RAG-miss vs LLM-miss without re-running the pipeline.
Chunk retrieval data lives in Ali's rag_chunk_metadata state channel
(emitted as rag_sources in the per-trial JSON output) and is read from
there at categorization time, so we do not duplicate it here.

Uses a module-level current-trace global because the pipeline runs
sequentially in a single process; threading a trace object through every
LangGraph node would require touching ~10 files for no functional gain.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class LlmNodeTrace:
    node: str
    system_prompt: str
    user_prompt: str
    response: str
    model: str | None
    input_tokens: int | None
    output_tokens: int | None
    cached: bool | None
    latency_ms: int
    cache_hit: bool
    parse_error: str | None
    parsed_answers: dict[str, Any] | None
    is_repair: bool = False
    # Chain-of-thought from providers that emit it (e.g. gpt-oss via OpenRouter).
    # Used at categorization time to tell whether the model reasoned over the
    # retrieved chunks or ignored them. None when the provider does not emit one.
    reasoning_content: str | None = None


@dataclass
class PipelineTrace:
    trial: str
    outcome: str | None
    timestamp_start: str
    timestamp_end: str | None = None
    llm_calls: list[LlmNodeTrace] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, default=str)

    def write(self, output_dir: Path | str) -> Path:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{self.trial}_trace.json"
        path.write_text(self.to_json(), encoding="utf-8")
        return path


_CURRENT_TRACE: PipelineTrace | None = None


def start_trace(trial: str, outcome: str | None) -> PipelineTrace:
    global _CURRENT_TRACE
    _CURRENT_TRACE = PipelineTrace(
        trial=trial,
        outcome=outcome,
        timestamp_start=datetime.now(timezone.utc).isoformat(),
    )
    return _CURRENT_TRACE


def end_trace() -> PipelineTrace | None:
    global _CURRENT_TRACE
    trace = _CURRENT_TRACE
    if trace is not None:
        trace.timestamp_end = datetime.now(timezone.utc).isoformat()
    _CURRENT_TRACE = None
    return trace


def get_current_trace() -> PipelineTrace | None:
    return _CURRENT_TRACE


def append_llm_call(
    node: str,
    system_prompt: str,
    user_prompt: str,
    response: str,
    model: str | None,
    input_tokens: int | None,
    output_tokens: int | None,
    cached: bool | None,
    latency_ms: int,
    cache_hit: bool,
    parse_error: str | None = None,
    parsed_answers: dict[str, Any] | None = None,
    is_repair: bool = False,
    reasoning_content: str | None = None,
) -> None:
    if _CURRENT_TRACE is None:
        return
    _CURRENT_TRACE.llm_calls.append(
        LlmNodeTrace(
            node=node,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response=response,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached=cached,
            latency_ms=latency_ms,
            cache_hit=cache_hit,
            parse_error=parse_error,
            parsed_answers=parsed_answers,
            is_repair=is_repair,
            reasoning_content=reasoning_content,
        )
    )
