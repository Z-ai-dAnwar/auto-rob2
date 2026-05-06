from rob2_pipeline.judges.domain3 import judge_domain3
from rob2_pipeline.nodes.common import add_domain_judgment, call_node_llm, merge_sq_answers, set_na
from rob2_pipeline.prompts import PROMPT_DOMAIN3
from rob2_pipeline.state import RoB2State
from rob2_pipeline.xml_parser import parse_sq_response


def domain3_sq_node(state: RoB2State) -> RoB2State:
    sections = state["sections"]
    prompt = PROMPT_DOMAIN3.format(
        intervention=state["intervention"],
        comparator=state["comparator"],
        outcome=state["outcome"],
        n_randomized=state.get("n_randomized", "Not reported"),
        consort_text=sections.get("consort", ""),
        missing_data_text=sections.get("missing_data", "") or sections.get("results", ""),
        sensitivity_text=sections.get("analysis", ""),
    )
    response, log = call_node_llm(state, prompt, "domain3_sq")
    sq_answers = merge_sq_answers(state, parse_sq_response(response, ["3.1", "3.2", "3.3", "3.4"]))
    s31 = sq_answers.get("3.1", {}).get("answer", "NI")
    s32 = sq_answers.get("3.2", {}).get("answer", "NA")
    s33 = sq_answers.get("3.3", {}).get("answer", "NA")
    if s31 in ("Y", "PY"):
        sq_answers = set_na(sq_answers, "3.2", "3.3", "3.4")
    elif s32 in ("Y", "PY"):
        sq_answers = set_na(sq_answers, "3.3", "3.4")
    elif s33 in ("N", "PN"):
        sq_answers = set_na(sq_answers, "3.4")
    return {**state, "sq_answers": sq_answers, "llm_call_log": log}


def domain3_judge_node(state: RoB2State) -> RoB2State:
    judgment, rationale = judge_domain3(state["sq_answers"])
    return add_domain_judgment(state, "D3", judgment, rationale)
