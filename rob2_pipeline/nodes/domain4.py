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
        outcome_type=state.get("outcome_type", "clinician-composite"),
        sq_2_1=sq21,
        outcome_measurement_text=sections.get("outcomes", "") or sections.get("methods", ""),
        blinding_text=sections.get("blinding", ""),
    )
    response, log, parsed = call_node_llm(
        state, prompt, "domain4_sq", parse_sq_response, ["4.1", "4.2", "4.3", "4.4", "4.5"]
    )
    parsed_sqs = parsed or {}

    outcome_type = state.get("outcome_type", "clinician-composite")
    sq_2_1 = state.get("sq_answers", {}).get("2.1", {}).get("answer", "NI")

    if outcome_type == "patient-reported" and sq_2_1 in ("Y", "PY"):
        parsed_sqs["4.3"] = {
            "answer": "Y",
            "quote": "Auto-set: patient-reported outcome with participants aware of assignment",
            "justification": "Per Sterne et al. 2019: for participant-reported outcomes, the assessor is the participant, who cannot be blinded to their own treatment assignment.",
            "uncertainty_flag": "NORMAL",
        }

    if outcome_type in ("vital-status", "biomarker"):
        parsed_sqs["4.4"] = {
            "answer": "N",
            "quote": "Auto-set: vital-status or biomarker outcome",
            "justification": "Per Sterne et al. 2019: knowledge is unlikely to influence vital-status or biomarker outcomes without judgment (e.g., all-cause mortality).",
            "uncertainty_flag": "NORMAL",
        }

    sq_answers = merge_sq_answers(state, parsed_sqs)
    s41 = sq_answers.get("4.1", {}).get("answer", "NI")
    s42 = sq_answers.get("4.2", {}).get("answer", "NI")
    s43 = sq_answers.get("4.3", {}).get("answer", "NA")
    s44 = sq_answers.get("4.4", {}).get("answer", "NA")
    if s41 in ("Y", "PY") or s42 in ("Y", "PY"):
        sq_answers = set_na(sq_answers, "4.3", "4.4", "4.5")
    elif s43 in ("N", "PN"):
        sq_answers = set_na(sq_answers, "4.4", "4.5")
    elif s44 in ("N", "PN"):
        sq_answers = set_na(sq_answers, "4.5")
    return {"sq_answers": sq_answers, "llm_call_log": log}


def domain4_judge_node(state: RoB2State) -> RoB2State:
    judgment, rationale = judge_domain4(state["sq_answers"])
    return add_domain_judgment(state, "D4", judgment, rationale)
