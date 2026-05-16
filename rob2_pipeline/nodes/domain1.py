from rob2_pipeline.judges.domain1 import judge_domain1
from rob2_pipeline.models import format_evidence
from rob2_pipeline.nodes.common import (
    add_domain_judgment,
    call_node_llm,
    call_node_llm_with_sources,
    format_chunk_sources,
    merge_sq_answers,
)
from rob2_pipeline.nodes.evidence_packets import packet_block_for_domain
from rob2_pipeline.prompts import PROMPT_DOMAIN1
from rob2_pipeline.state import RoB2State
from rob2_pipeline.xml_parser import parse_sq_response


def domain1_sq_node(state: RoB2State) -> RoB2State:
    evidence = state["evidence"]
    rag_contexts = state.get("rag_contexts", {})
    trial_facts = state.get("trial_facts", {})
    trial_level_text = "\n".join(
        part
        for part in [
            trial_facts.get("randomization", ""),
            trial_facts.get("allocation_concealment", ""),
        ]
        if part
    )
    packet_text = packet_block_for_domain(state.get("evidence_packets", {}), "d1")
    prompt = PROMPT_DOMAIN1.format(
        intervention=state["intervention"],
        comparator=state["comparator"],
        outcome=state["outcome"],
        randomization_text="\n\n".join(
            part
            for part in [format_evidence(evidence["d1_randomization"]) or format_evidence(evidence["methods"]), trial_level_text]
            if part
        ),
        baseline_text=format_evidence(evidence["baseline_table"]),
        consort_text=format_evidence(evidence["consort_flow"]),
        rag_text="\n\n".join(part for part in [packet_text, rag_contexts.get("d1", "")] if part),
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
