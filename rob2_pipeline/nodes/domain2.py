from rob2_pipeline.judges.domain2 import judge_domain2
from rob2_pipeline.nodes.common import add_domain_judgment, call_node_llm, merge_sq_answers, set_na
from rob2_pipeline.prompts import (
    PROMPT_DOMAIN2_ADHERING_ANALYSIS,
    PROMPT_DOMAIN2_ADHERING_CONDITIONAL,
    PROMPT_DOMAIN2_ANALYSIS,
    PROMPT_DOMAIN2_CONDITIONAL,
    PROMPT_DOMAIN2_SQ12,
)
from rob2_pipeline.state import RoB2State
from rob2_pipeline.xml_parser import parse_sq_response


def domain2_sq12_node(state: RoB2State) -> RoB2State:
    sections = state["sections"]
    prompt = PROMPT_DOMAIN2_SQ12.format(
        intervention=state["intervention"],
        comparator=state["comparator"],
        outcome=state["outcome"],
        blinding_text=sections.get("blinding", ""),
        methods_text=sections.get("methods", ""),
    )
    response, log, parsed = call_node_llm(
        state, prompt, "domain2_sq12", parse_sq_response, ["2.1", "2.2"]
    )
    sq_answers = merge_sq_answers(state, parsed or {})
    s21 = sq_answers.get("2.1", {}).get("answer", "NI")
    s22 = sq_answers.get("2.2", {}).get("answer", "NI")
    if state.get("effect_of_interest", "ITT").lower() != "per-protocol" and s21 in ("N", "PN") and s22 in ("N", "PN"):
        sq_answers = set_na(sq_answers, "2.3", "2.4", "2.5")
    return {"sq_answers": sq_answers, "llm_call_log": log}


def d2_needs_conditional(state: RoB2State) -> str:
    if state.get("effect_of_interest", "ITT").lower() == "per-protocol":
        return "conditional"
    s21 = state["sq_answers"].get("2.1", {}).get("answer", "NI")
    s22 = state["sq_answers"].get("2.2", {}).get("answer", "NI")
    if s21 in ("N", "PN") and s22 in ("N", "PN"):
        return "analysis"
    return "conditional"


def domain2_conditional_node(state: RoB2State) -> RoB2State:
    sections = state["sections"]
    sq = state["sq_answers"]
    prompt_template = (
        PROMPT_DOMAIN2_ADHERING_CONDITIONAL
        if state.get("effect_of_interest", "ITT").lower() == "per-protocol"
        else PROMPT_DOMAIN2_CONDITIONAL
    )
    prompt = prompt_template.format(
        intervention=state["intervention"],
        comparator=state["comparator"],
        outcome=state["outcome"],
        sq_2_1=sq.get("2.1", {}).get("answer", "NI"),
        sq_2_2=sq.get("2.2", {}).get("answer", "NI"),
        deviations_text=sections.get("methods", "") + "\n" + sections.get("results", ""),
        concomitant_text=sections.get("methods", ""),
    )
    response, log, parsed = call_node_llm(
        state, prompt, "domain2_conditional", parse_sq_response, ["2.3", "2.4", "2.5"]
    )
    sq_answers = merge_sq_answers(state, parsed or {})
    if state.get("effect_of_interest", "ITT").lower() == "per-protocol":
        return {"sq_answers": sq_answers, "llm_call_log": log}
    s23 = sq_answers.get("2.3", {}).get("answer", "NI")
    s24 = sq_answers.get("2.4", {}).get("answer", "NI")
    if s23 in ("N", "PN", "NI"):
        sq_answers = set_na(sq_answers, "2.4", "2.5")
    elif s24 in ("N", "PN", "NA"):
        sq_answers = set_na(sq_answers, "2.5")
    return {"sq_answers": sq_answers, "llm_call_log": log}


def domain2_analysis_node(state: RoB2State) -> RoB2State:
    sections = state["sections"]
    prompt_template = (
        PROMPT_DOMAIN2_ADHERING_ANALYSIS
        if state.get("effect_of_interest", "ITT").lower() == "per-protocol"
        else PROMPT_DOMAIN2_ANALYSIS
    )
    prompt = prompt_template.format(
        intervention=state["intervention"],
        comparator=state["comparator"],
        outcome=state["outcome"],
        effect_of_interest=state.get("effect_of_interest", "ITT"),
        analysis_text=sections.get("analysis", ""),
        results_text=sections.get("results", ""),
    )
    response, log, parsed = call_node_llm(
        state, prompt, "domain2_analysis", parse_sq_response, ["2.6", "2.7"]
    )
    sq_answers = merge_sq_answers(state, parsed or {})
    if state.get("effect_of_interest", "ITT").lower() == "per-protocol" or sq_answers.get("2.6", {}).get("answer", "NI") in ("Y", "PY"):
        sq_answers = set_na(sq_answers, "2.7")
    return {"sq_answers": sq_answers, "llm_call_log": log}


def domain2_judge_node(state: RoB2State) -> RoB2State:
    judgment, rationale = judge_domain2(state["sq_answers"], state.get("effect_of_interest", "ITT"))
    return add_domain_judgment(state, "D2", judgment, rationale)
