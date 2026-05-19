from collections.abc import Callable

from rob2_pipeline.nodes.common import (
    call_node_llm,
    call_node_llm_with_sources,
    format_chunk_sources,
    merge_sq_answers,
)
from rob2_pipeline.state import RoB2State
from rob2_pipeline.xml_parser import parse_sq_response


def call_domain_sq_prompt(
    state: RoB2State,
    prompt: str,
    *,
    node_name: str,
    sq_ids: list[str],
    source_domain: str,
    parse_fn: Callable = parse_sq_response,
) -> tuple[dict[str, dict], list[dict]]:
    _response, log, parsed = call_node_llm_with_sources(
        call_node_llm,
        state,
        prompt,
        node_name,
        parse_fn,
        sq_ids,
        chunk_sources=format_chunk_sources(state, source_domain),
    )
    return merge_sq_answers(state, parsed or {}), log
