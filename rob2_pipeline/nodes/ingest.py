from rob2_pipeline.nodes.common import call_node_llm
from rob2_pipeline.pdf_ingestion import extract_full_text, parse_sections, section_debug_summary
from rob2_pipeline.prompts import PROMPT_RCT_SCREEN
from rob2_pipeline.state import RoB2State
from rob2_pipeline.xml_parser import extract_tag


def pdf_ingest_node(state: RoB2State) -> RoB2State:
    full_text = extract_full_text(state["pdf_path"])
    sections = parse_sections(full_text)
    return {
        **state,
        "full_text": full_text,
        "sections": sections,
        "errors": list(state.get("errors", [])),
        "llm_call_log": list(state.get("llm_call_log", [])),
        "sq_answers": dict(state.get("sq_answers", {})),
        "domain_judgments": dict(state.get("domain_judgments", {})),
        "domain_rationales": dict(state.get("domain_rationales", {})),
    }


def rct_screener_node(state: RoB2State) -> RoB2State:
    sections = state["sections"]
    methods_text = "\n\n".join(
        part
        for part in [
            sections.get("abstract", ""),
            sections.get("methods", ""),
            sections.get("randomization", ""),
            sections.get("consort", ""),
        ]
        if part
    )
    prompt = PROMPT_RCT_SCREEN.format(methods_text=methods_text)
    response, log = call_node_llm(state, prompt, "rct_screener")
    is_rct = (extract_tag(response, "is_rct") or "NO").strip().upper() == "YES"
    evidence = extract_tag(response, "evidence") or "No relevant text found"
    errors = list(state.get("errors", []))
    if not is_rct:
        errors.append("Study screened as non-RCT; RoB 2 assessment stopped.")
    return {**state, "is_rct": is_rct, "rct_screen_evidence": evidence, "errors": errors, "llm_call_log": log}


def section_parser_node(state: RoB2State) -> RoB2State:
    sections = parse_sections(state.get("full_text", ""))
    return {**state, "sections": sections, "__debug_sections": section_debug_summary(sections)}
