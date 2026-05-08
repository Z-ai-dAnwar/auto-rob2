import time
from typing import Callable, Optional

from langchain_core.messages import HumanMessage

from rob2_pipeline import llm_client
from rob2_pipeline.cache import read_cache, write_cache
from rob2_pipeline.types import LLMCallLogEntry
from rob2_pipeline.xml_parser import validate_sq_answers


SYSTEM_MESSAGE = (
    "You are an expert systematic reviewer applying the Cochrane Risk of Bias 2 "
    "(RoB 2) tool. Respond only in the XML format specified in the prompt. "
    "Do not add preamble, explanation, or markdown code fences around your XML."
)

NA_ANSWER = {
    "answer": "NA",
    "quote": "Not applicable",
    "justification": "Not applicable",
    "uncertainty_flag": "NORMAL",
}


def call_node_llm(
    state: dict,
    prompt: str,
    node_name: str,
    parse_fn: Optional[Callable[[str, list[str]], dict[str, dict]]] = None,
    parse_sq_ids: Optional[list[str]] = None,
) -> tuple[str, list[LLMCallLogEntry], Optional[dict[str, dict]]]:
    """Call LLM for a node with optional cache and parser validation."""

    def _parse_and_validate(raw: str) -> Optional[dict[str, dict]]:
        if not (parse_fn and parse_sq_ids):
            return None
        parsed_local = parse_fn(raw, parse_sq_ids)
        validate_sq_answers(parsed_local, parse_sq_ids)
        return parsed_local

    cached = read_cache(node_name, prompt)
    log: list[LLMCallLogEntry] = []

    if cached is not None:
        log_entry = {
            "node": node_name,
            "prompt_length_chars": len(prompt),
            "response_length_chars": len(cached),
            "latency_ms": 0,
            "cache_hit": True,
        }
        parsed = _parse_and_validate(cached)
        log.append(log_entry)
        return cached, log, parsed

    llm = llm_client.get_llm()
    start = time.perf_counter()
    response = llm_client.call_llm(
        llm, [HumanMessage(content=prompt)], node_name=node_name, system_message=SYSTEM_MESSAGE
    )
    parsed = None
    parse_error = None
    if parse_fn and parse_sq_ids:
        try:
            parsed = _parse_and_validate(response)
        except Exception as exc:  # noqa: BLE001
            parse_error = exc
            repair_prompt = (
                f"Your previous response for {node_name} was invalid: {exc}. "
                "Return only well-formed XML in exactly the requested schema.\n\n"
                f"Original prompt:\n{prompt}"
            )
            response = llm_client.call_llm(
                llm,
                [HumanMessage(content=repair_prompt)],
                node_name=node_name,
                system_message=SYSTEM_MESSAGE,
            )
            parsed = _parse_and_validate(response)
            parse_error = None
    latency_ms = int((time.perf_counter() - start) * 1000)
    write_cache(node_name, prompt, response)
    log_entry = {
        "node": node_name,
        "prompt_length_chars": len(prompt),
        "response_length_chars": len(response),
        "latency_ms": latency_ms,
        "cache_hit": False,
    }
    if parse_error is not None:
        log_entry["parse_error"] = str(parse_error)
    log.append(log_entry)
    return response, log, parsed


def merge_sq_answers(state: dict, parsed: dict[str, dict]) -> dict[str, dict]:
    sq_answers = dict(state.get("sq_answers", {}))
    sq_answers.update(parsed)
    return sq_answers


def set_na(sq_answers: dict[str, dict], *sq_ids: str) -> dict[str, dict]:
    updated = dict(sq_answers)
    for sq_id in sq_ids:
        updated[sq_id] = dict(NA_ANSWER)
    return updated


def add_domain_judgment(state: dict, domain: str, judgment: str, rationale: str) -> dict:
    domain_judgments = dict(state.get("domain_judgments", {}))
    domain_rationales = dict(state.get("domain_rationales", {}))
    domain_judgments[domain] = judgment
    domain_rationales[domain] = rationale
    return {"domain_judgments": domain_judgments, "domain_rationales": domain_rationales}
