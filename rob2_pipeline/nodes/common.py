import time

from langchain_core.messages import HumanMessage

from rob2_pipeline import llm_client


NA_ANSWER = {
    "answer": "NA",
    "quote": "Not applicable",
    "justification": "Not applicable",
    "uncertainty_flag": "NORMAL",
}


def call_node_llm(state: dict, prompt: str, node_name: str) -> tuple[str, list[dict]]:
    llm = llm_client.get_llm()
    start = time.perf_counter()
    response = llm_client.call_llm(llm, [HumanMessage(content=prompt)], node_name=node_name)
    latency_ms = int((time.perf_counter() - start) * 1000)
    log = list(state.get("llm_call_log", []))
    log.append(
        {
            "node": node_name,
            "prompt_length_chars": len(prompt),
            "response_length_chars": len(response),
            "latency_ms": latency_ms,
        }
    )
    return response, log


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
    return {**state, "domain_judgments": domain_judgments, "domain_rationales": domain_rationales}
