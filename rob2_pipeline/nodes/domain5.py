from rob2_pipeline.judges.domain5 import judge_domain5
from rob2_pipeline.models import format_evidence
from rob2_pipeline.nodes.common import add_domain_judgment, call_node_llm, merge_sq_answers
from rob2_pipeline.prompts import PROMPT_DOMAIN5
from rob2_pipeline.state import RoB2State
from rob2_pipeline.xml_parser import parse_sq_response


def domain5_sq_node(state: RoB2State) -> RoB2State:
    evidence = state["evidence"]
    rag_contexts = state.get("rag_contexts", {})
    errors = list(state.get("errors", []))
    human_review_priority = state.get("human_review_priority", "HIGH")
    if state.get("intervention") == "Not reported":
        errors.append("Intervention not reported; manual review required for Domain 5 assessment.")
        human_review_priority = "HIGH"
    prompt = PROMPT_DOMAIN5.format(
        intervention=state["intervention"],
        comparator=state["comparator"],
        outcome=state["outcome"],
        numerical_result=state.get("numerical_result", "Not reported"),
        registration_number=state.get("registration_number", "Not reported"),
        registered_endpoint=state.get("registered_endpoint", "Not reported"),
        registered_secondary_endpoints=state.get("registered_secondary_endpoints", "Not reported"),
        reported_endpoint=state.get("outcome", "Not reported"),
        ctgov_outcomes=state.get("ctgov_outcomes", ""),
        registration_text=rag_contexts.get("d5") or format_evidence(evidence["d5_registration"]),
        sap_text="" if rag_contexts.get("d5") else format_evidence(evidence["d4_outcome_meas"]),
        results_text="" if rag_contexts.get("d5") else format_evidence(evidence["results"]),
    )
    response, log, parsed = call_node_llm(
        state, prompt, "domain5_sq", parse_sq_response, ["5.1", "5.2", "5.3"]
    )
    sq_answers = merge_sq_answers(state, parsed or {})
    return {
        "sq_answers": sq_answers,
        "llm_call_log": log,
        "errors": errors,
        "human_review_priority": human_review_priority,
    }


def domain5_judge_node(state: RoB2State) -> RoB2State:
    judgment, rationale = judge_domain5(state["sq_answers"])
    return add_domain_judgment(state, "D5", judgment, rationale)
