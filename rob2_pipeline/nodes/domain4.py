from rob2_pipeline.judges.domain4 import judge_domain4
from rob2_pipeline.nodes.common import add_domain_judgment, call_node_llm, merge_sq_answers, set_na
from rob2_pipeline.prompts import PROMPT_DOMAIN4
from rob2_pipeline.state import RoB2State
from rob2_pipeline.xml_parser import parse_sq_response


def domain4_sq_node(state: RoB2State) -> RoB2State:
    sections = state["sections"]
    sq21 = state.get("sq_answers", {}).get("2.1", {}).get("answer", "NI")
    prompt = PROMPT_DOMAIN4.format(
        intervention=state["intervention"],
        comparator=state["comparator"],
        outcome=state["outcome"],
        outcome_type=state.get("outcome_type", "objective"),
        sq_2_1=sq21,
        outcome_measurement_text=sections.get("outcomes", "") or sections.get("methods", ""),
        blinding_text=sections.get("blinding", ""),
    )
    response, log = call_node_llm(state, prompt, "domain4_sq")
    sq_answers = merge_sq_answers(state, parse_sq_response(response, ["4.1", "4.2", "4.3", "4.4", "4.5"]))
    s41 = sq_answers.get("4.1", {}).get("answer", "NI")
    s42 = sq_answers.get("4.2", {}).get("answer", "NI")
    s43 = sq_answers.get("4.3", {}).get("answer", "NA")
    s44 = sq_answers.get("4.4", {}).get("answer", "NA")
    if s41 in ("Y", "PY") or s42 in ("Y", "PY"):
        sq_answers = set_na(sq_answers, "4.3", "4.4", "4.5")
    elif state.get("outcome_type") == "patient-reported" and sq21 in ("Y", "PY"):
        sq_answers["4.3"] = {
            "answer": "Y",
            "quote": f"Auto-set: patient-reported outcome, Q2.1={sq21}",
            "justification": "Participants are the outcome assessors for patient-reported outcomes and were aware of assignment.",
            "uncertainty_flag": "NORMAL",
        }
    elif s43 in ("N", "PN"):
        sq_answers = set_na(sq_answers, "4.4", "4.5")
    elif s44 in ("N", "PN"):
        sq_answers = set_na(sq_answers, "4.5")
    return {**state, "sq_answers": sq_answers, "llm_call_log": log}


def domain4_judge_node(state: RoB2State) -> RoB2State:
    judgment, rationale = judge_domain4(state["sq_answers"])
    return add_domain_judgment(state, "D4", judgment, rationale)
