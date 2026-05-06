from rob2_pipeline.judges.domain1 import judge_domain1
from rob2_pipeline.nodes.common import add_domain_judgment, call_node_llm, merge_sq_answers
from rob2_pipeline.prompts import PROMPT_DOMAIN1
from rob2_pipeline.state import RoB2State
from rob2_pipeline.xml_parser import parse_sq_response


def domain1_sq_node(state: RoB2State) -> RoB2State:
    sections = state["sections"]
    prompt = PROMPT_DOMAIN1.format(
        intervention=state["intervention"],
        comparator=state["comparator"],
        outcome=state["outcome"],
        randomization_text=sections.get("randomization", "") or sections.get("methods", ""),
        baseline_text=sections.get("baseline", ""),
        consort_text=sections.get("consort", ""),
    )
    response, log = call_node_llm(state, prompt, "domain1_sq")
    sq_answers = merge_sq_answers(state, parse_sq_response(response, ["1.1", "1.2", "1.3"]))
    return {**state, "sq_answers": sq_answers, "llm_call_log": log}


def domain1_judge_node(state: RoB2State) -> RoB2State:
    judgment, rationale = judge_domain1(state["sq_answers"])
    return add_domain_judgment(state, "D1", judgment, rationale)
