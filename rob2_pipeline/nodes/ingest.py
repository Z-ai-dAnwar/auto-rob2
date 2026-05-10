from rob2_pipeline.nodes.common import call_node_llm
from rob2_pipeline.models import format_evidence
from rob2_pipeline.pdf_ingestion import (
    _configure_docling_runtime,
    _get_docling_converter,
    allow_remote_evidence_extraction,
    appears_rct_candidate,
    build_document_repr,
    extract_paper_evidence,
    extract_full_text,
    extract_structural_paper_evidence,
    paper_evidence_from_sections,
    parse_sections,
)
from rob2_pipeline.prompts import PROMPT_RCT_SCREEN
from rob2_pipeline.state import RoB2State
from rob2_pipeline.xml_parser import extract_tag


def pdf_ingest_node(state: RoB2State) -> RoB2State:
    pdf_path = state["pdf_path"]
    full_text = extract_full_text(pdf_path)

    try:
        _configure_docling_runtime()
        converter = _get_docling_converter(use_ocr=False)
        conv_result = converter.convert(pdf_path)
        doc = conv_result.document
        doc_repr = build_document_repr(doc)
        if not doc_repr.full_text:
            doc_repr.full_text = full_text
        evidence = extract_structural_paper_evidence(doc_repr)
        if not allow_remote_evidence_extraction():
            evidence["warnings"].append("Remote evidence extraction disabled by ROB2_REMOTE_EVIDENCE_EXTRACTION.")
            return {"full_text": full_text, "evidence": evidence, "docling_doc": conv_result}
        if not appears_rct_candidate(doc_repr.to_prompt_repr() or doc_repr.full_text):
            evidence["warnings"].append("Remote evidence extraction skipped for apparent non-RCT document.")
            return {"full_text": full_text, "evidence": evidence, "docling_doc": conv_result}
        try:
            evidence, log = extract_paper_evidence(doc_repr)
            return {"full_text": full_text, "evidence": evidence, "docling_doc": conv_result, "llm_call_log": log}
        except Exception as error:  # noqa: BLE001
            evidence = extract_structural_paper_evidence(doc_repr)
            evidence["warnings"].append(f"LLM evidence extraction failed: {error}")
            return {"full_text": full_text, "evidence": evidence, "docling_doc": conv_result}
    except Exception:
        sections = parse_sections(full_text)
        evidence = paper_evidence_from_sections(
            sections,
            extraction_method="fallback",
            source="keyword_fallback",
            warnings=["Docling structural extraction failed; used text keyword fallback."],
        )
        return {"full_text": full_text, "evidence": evidence, "docling_doc": None}


def rct_screener_node(state: RoB2State) -> RoB2State:
    evidence = state["evidence"]
    methods_text = "\n\n".join(
        part
        for part in [
            format_evidence(evidence["abstract"]),
            format_evidence(evidence["methods"]),
            format_evidence(evidence["d1_randomization"]),
            format_evidence(evidence["consort_flow"]),
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
