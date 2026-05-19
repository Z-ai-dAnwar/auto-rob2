from rob2_pipeline.judges.domain5 import judge_domain5
from rob2_pipeline.models import format_evidence
from rob2_pipeline.nodes.common import (
    add_domain_judgment,
)
from rob2_pipeline.nodes.domain_helpers import call_domain_sq_prompt
from rob2_pipeline.nodes.evidence_packets import packet_block_for_domain
from rob2_pipeline.prompts import PROMPT_DOMAIN5
from rob2_pipeline.state import RoB2State


def domain5_sq_node(state: RoB2State) -> RoB2State:
    evidence = state["evidence"]
    rag_contexts = state.get("rag_contexts", {})
    packet_text = packet_block_for_domain(state.get("evidence_packets", {}), "d5")
    errors = list(state.get("errors", []))
    human_review_priority = state.get("human_review_priority", "HIGH")
    if state.get("intervention") == "Not reported":
        errors.append(
            "Intervention not reported; manual review required for Domain 5 assessment."
        )
        human_review_priority = "HIGH"
    prompt = PROMPT_DOMAIN5.format(
        intervention=state["intervention"],
        comparator=state["comparator"],
        outcome=state["outcome"],
        outcome_type=state.get("outcome_type", "clinician-composite"),
        numerical_result=state.get("numerical_result", "Not reported"),
        registration_number=state.get("registration_number", "Not reported"),
        registered_endpoint=state.get("registered_endpoint", "Not reported"),
        registered_secondary_endpoints=state.get(
            "registered_secondary_endpoints", "Not reported"
        ),
        reported_endpoint=state.get("outcome", "Not reported"),
        ctgov_outcomes=state.get("ctgov_outcomes", ""),
        ctgov_description=state.get(
            "ctgov_description", "(No ClinicalTrials.gov description available)"
        ),
        registration_text=format_evidence(evidence["d5_registration"]),
        sap_text=format_evidence(evidence["d4_outcome_meas"]),
        results_text=format_evidence(evidence["results"]),
        rag_text="\n\n".join(
            part for part in [packet_text, rag_contexts.get("d5", "")] if part
        ),
    )
    sq_answers, log = call_domain_sq_prompt(
        state,
        prompt,
        node_name="domain5_sq",
        sq_ids=["5.1", "5.2", "5.3"],
        source_domain="d5",
    )
    return {
        "sq_answers": sq_answers,
        "llm_call_log": log,
        "errors": errors,
        "human_review_priority": human_review_priority,
    }


def domain5_judge_node(state: RoB2State) -> RoB2State:
    judgment, rationale = judge_domain5(state["sq_answers"])
    return add_domain_judgment(state, "D5", judgment, rationale)
