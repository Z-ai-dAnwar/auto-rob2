from rob2_pipeline.judges.domain5 import judge_domain5
from rob2_pipeline.nodes.common import add_domain_judgment, call_node_llm, merge_sq_answers
from rob2_pipeline.prompts import PROMPT_DOMAIN5
from rob2_pipeline.state import RoB2State
from rob2_pipeline.xml_parser import parse_sq_response


def domain5_sq_node(state: RoB2State) -> RoB2State:
    sections = state["sections"]
    prompt = PROMPT_DOMAIN5.format(
        intervention=state["intervention"],
        comparator=state["comparator"],
        outcome=state["outcome"],
        numerical_result=state.get("numerical_result", "Not reported"),
        registration_number=state.get("registration_number", "Not reported"),
        registered_endpoint="Not reported",
        reported_endpoint=state.get("outcome", "Not reported"),
        registration_text=sections.get("registration", ""),
        sap_text=sections.get("analysis", ""),
        results_text=sections.get("results", ""),
    )
    response, log = call_node_llm(state, prompt, "domain5_sq")
    sq_answers = merge_sq_answers(state, parse_sq_response(response, ["5.1", "5.2", "5.3"]))
    return {**state, "sq_answers": sq_answers, "llm_call_log": log}


def domain5_judge_node(state: RoB2State) -> RoB2State:
    judgment, rationale = judge_domain5(state["sq_answers"])
    return add_domain_judgment(state, "D5", judgment, rationale)
