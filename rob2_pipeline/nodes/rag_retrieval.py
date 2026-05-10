from rob2_pipeline.models import PaperEvidence, format_evidence
from rob2_pipeline.pdf_ingestion import extract_censoring_context
from rob2_pipeline.rag import build_index, chunk_docling_doc, retrieve
from rob2_pipeline.rag_queries import DOMAIN_QUERIES
from rob2_pipeline.state import RoB2State


def _sections_fallback(evidence: PaperEvidence) -> dict[str, str]:
    return {
        "d1": "\n\n".join(
            part
            for part in [
                format_evidence(evidence["d1_randomization"]),
                format_evidence(evidence["baseline_table"]),
                format_evidence(evidence["consort_flow"]),
            ]
            if part
        ),
        "d2_blinding": format_evidence(evidence["d2_blinding"]),
        "d2_deviations": "\n\n".join(
            part
            for part in [format_evidence(evidence["d2_blinding"]), format_evidence(evidence["methods"])]
            if part
        ),
        "d2_analysis": "\n\n".join(
            part
            for part in [format_evidence(evidence["d4_outcome_meas"]), format_evidence(evidence["results"])]
            if part
        ),
        "d3": "\n\n".join(
            part
            for part in [format_evidence(evidence["d3_missing_data"]), format_evidence(evidence["consort_flow"])]
            if part
        ),
        "d4_measurement": format_evidence(evidence["d4_outcome_meas"]),
        "d4_assessor": format_evidence(evidence["d2_blinding"]),
        "d5": "\n\n".join(
            part
            for part in [format_evidence(evidence["d5_registration"]), format_evidence(evidence["results"])]
            if part
        ),
    }


def rag_retrieval_node(state: RoB2State) -> dict:
    conv_result = state.get("docling_doc")
    if conv_result is None:
        rag_contexts = _sections_fallback(state["evidence"])
    else:
        try:
            chunks = chunk_docling_doc(conv_result)
            index, chunks = build_index(chunks)
            rag_contexts = {
                key: retrieve(index, chunks, queries)
                for key, queries in DOMAIN_QUERIES.items()
            }
        except Exception as error:  # noqa: BLE001
            rag_contexts = _sections_fallback(state["evidence"])
            state["evidence"]["warnings"].append(f"RAG retrieval failed: {error}")

    censoring = extract_censoring_context(state.get("full_text", ""), state.get("outcome", ""))
    if censoring:
        rag_contexts["d3"] = (rag_contexts.get("d3", "") + "\n\n" + censoring).strip()
    return {"rag_contexts": rag_contexts}
