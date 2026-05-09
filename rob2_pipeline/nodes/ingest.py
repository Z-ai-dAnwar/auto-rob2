from rob2_pipeline.nodes.common import call_node_llm
from rob2_pipeline.pdf_ingestion import (
    _configure_docling_runtime,
    _get_docling_converter,
    _parse_sections_from_docling_document,
    extract_full_text,
    parse_sections,
)
from rob2_pipeline.prompts import PROMPT_RCT_SCREEN
from rob2_pipeline.state import RoB2State
from rob2_pipeline.xml_parser import extract_tag


def pdf_ingest_node(state: RoB2State) -> RoB2State:
    pdf_path = state["pdf_path"]
    full_text = extract_full_text(pdf_path)

    sections = None
    try:
        _configure_docling_runtime()
        converter = _get_docling_converter(use_ocr=False)
        doc = converter.convert(pdf_path).document
        sections = _parse_sections_from_docling_document(doc)
    except Exception:
        sections = None

    if sections is None:
        sections = parse_sections(full_text)

    return {"full_text": full_text, "sections": sections}


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
    response, log, _ = call_node_llm(state, prompt, "rct_screener")
    is_rct = (extract_tag(response, "is_rct") or "NO").strip().upper() == "YES"
    evidence = extract_tag(response, "evidence") or "No relevant text found"
    errors = list(state.get("errors", []))
    if not is_rct:
        errors.append("Study screened as non-RCT; RoB 2 assessment stopped.")
    return {"is_rct": is_rct, "rct_screen_evidence": evidence, "errors": errors, "llm_call_log": log}
