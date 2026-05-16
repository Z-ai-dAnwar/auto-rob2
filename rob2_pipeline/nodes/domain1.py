from rob2_pipeline.judges.domain1 import judge_domain1
from rob2_pipeline.models import format_evidence
from rob2_pipeline.nodes.common import (
    add_domain_judgment,
    call_node_llm,
    call_node_llm_with_sources,
    format_chunk_sources,
    merge_sq_answers,
)
from rob2_pipeline.prompts import PROMPT_DOMAIN1
from rob2_pipeline.state import RoB2State
from rob2_pipeline.xml_parser import parse_sq_response


def domain1_sq_node(state: RoB2State) -> RoB2State:
    evidence = state["evidence"]
    rag_contexts = state.get("rag_contexts", {})
    prompt = PROMPT_DOMAIN1.format(
        intervention=state["intervention"],
        comparator=state["comparator"],
        outcome=state["outcome"],
        randomization_text=format_evidence(evidence["d1_randomization"]) or format_evidence(evidence["methods"]),
        baseline_text=format_evidence(evidence["baseline_table"]),
        consort_text=format_evidence(evidence["consort_flow"]),
        rag_text=rag_contexts.get("d1", ""),
        ctgov_design=state.get("ctgov_design", "(No ClinicalTrials.gov design metadata available)"),
    )
    response, log, parsed = call_node_llm_with_sources(
        call_node_llm,
        state,
        prompt,
        "domain1_sq",
        parse_sq_response,
        ["1.1", "1.2", "1.3"],
        chunk_sources=format_chunk_sources(state, "d1"),
    )
    sq_answers = merge_sq_answers(state, parsed or {})
    return {"sq_answers": sq_answers, "llm_call_log": log}


def domain1_judge_node(state: RoB2State) -> RoB2State:
    judgment, rationale = judge_domain1(state["sq_answers"])
    return add_domain_judgment(state, "D1", judgment, rationale)
