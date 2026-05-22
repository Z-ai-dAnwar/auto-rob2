from __future__ import annotations

import os
from pathlib import Path

from langchain_core.documents import Document

from rob2_pipeline.types import SourceDocument


DEFAULT_SUPPLEMENT_PAGE_WINDOW = 20
DEFAULT_SUPPLEMENT_MAX_SCAN_PAGES = 1000
_SUPPLEMENT_CONVERTER = None


def classify_supplement(path: Path) -> str:
    name = path.name.casefold()
    compact = name.replace("_", "-")
    if (
        "statistical-analysis" in compact
        or "analysis-plan" in compact
        or "sap" in compact
    ):
        return "sap"
    if "protocol" in compact:
        return "protocol"
    if (
        "data-sharing" in compact
        or compact.startswith("ds-")
        or compact.startswith("ds.")
        or compact.startswith("dss-")
        or compact.startswith("dss.")
    ):
        return "data_sharing"
    if "disclosure" in compact or "coi" in compact or "conflict" in compact:
        return "disclosure"
    if "appendix" in compact or "supplement" in compact or compact.startswith("mmc"):
        return "appendix"
    return "unknown_supplement"


def build_source_document(path: Path, role: str, index: int) -> SourceDocument:
    return SourceDocument(
        document_id=f"supplement:{index:03d}",
        document_name=path.name,
        document_role=role,
        source_kind="rag_chunk",
        path=str(path),
        is_primary=False,
        status="pending",
    )


def skipped_source_documents(
    paths: list[str], reason: str
) -> tuple[list[SourceDocument], list[str]]:
    documents: list[SourceDocument] = []
    warnings: list[str] = []
    for index, raw_path in enumerate(paths, start=1):
        path = Path(raw_path)
        source = build_source_document(path, classify_supplement(path), index)
        source["status"] = "failed"
        source["error"] = f"Supplement not ingested: {path}: {reason}"
        documents.append(source)
        warnings.append(source["error"])
    return documents, warnings


def primary_source_document(path: Path) -> SourceDocument:
    return SourceDocument(
        document_id="primary",
        document_name=path.name,
        document_role="primary",
        source_kind="rag_chunk",
        path=str(path),
        is_primary=True,
        status="parsed",
    )


def apply_source_metadata(chunks: list, source: SourceDocument) -> list:
    enriched = []
    for chunk in chunks:
        if not isinstance(chunk, Document):
            enriched.append(chunk)
            continue
        metadata = dict(chunk.metadata)
        metadata.update(
            {
                "document_id": source.get("document_id", ""),
                "document_name": source.get("document_name", ""),
                "document_role": source.get("document_role", ""),
                "source_kind": source.get("source_kind", "rag_chunk"),
                "source_path": source.get("path", ""),
            }
        )
        enriched.append(Document(page_content=chunk.page_content, metadata=metadata))
    return enriched


def ingest_supplements(
    paths: list[str],
) -> tuple[list[Document], list[SourceDocument], list[str]]:
    from rob2_pipeline.pdf_ingestion import (
        _configure_docling_runtime,
    )

    chunks: list[Document] = []
    documents: list[SourceDocument] = []
    warnings: list[str] = []
    if not paths:
        return chunks, documents, warnings

    for index, raw_path in enumerate(paths, start=1):
        path = Path(raw_path)
        role = classify_supplement(path)
        source = build_source_document(path, role, index)
        if not path.exists():
            source["status"] = "missing"
            source["error"] = f"Supplement not found: {path}"
            documents.append(source)
            warnings.append(source["error"])
            continue
        try:
            _configure_docling_runtime()
            converter = _get_supplement_converter()
            source_chunks, window_warnings = _convert_supplement_in_windows(
                converter, str(path), source
            )
            source["status"] = "partial" if window_warnings else "parsed"
            if window_warnings:
                source["error"] = "; ".join(window_warnings)
            chunks.extend(source_chunks)
            warnings.extend(window_warnings)
        except Exception as error:  # noqa: BLE001
            source["status"] = "failed"
            source["error"] = f"Supplement parse failed: {path}: {error}"
            warnings.append(source["error"])
        documents.append(source)
    return chunks, documents, warnings


def _convert_supplement_in_windows(
    converter, path: str, source: SourceDocument
) -> tuple[list[Document], list[str]]:
    from rob2_pipeline.pdf_ingestion import _build_docling_chunks

    all_chunks: list[Document] = []
    warnings: list[str] = []
    window_size = _supplement_page_window()
    max_scan_pages = _supplement_max_scan_pages()
    start = 1

    while start <= max_scan_pages:
        end = min(start + window_size - 1, max_scan_pages)
        try:
            conv_result = converter.convert(str(path), page_range=(start, end))
            window_chunks = apply_source_metadata(
                _build_docling_chunks(conv_result), source
            )
        except Exception as error:  # noqa: BLE001
            if _is_page_range_exhausted(error):
                break
            warnings.append(
                f"Supplement page window skipped: {path} pages {start}-{end}: {error}"
            )
            start = end + 1
            continue

        all_chunks.extend(window_chunks)
        start = end + 1

    return all_chunks, warnings


def _supplement_page_window() -> int:
    raw_value = os.getenv("ROB2_SUPPLEMENT_PAGE_WINDOW", "").strip()
    if not raw_value:
        return DEFAULT_SUPPLEMENT_PAGE_WINDOW
    try:
        window_size = int(raw_value)
    except ValueError:
        return DEFAULT_SUPPLEMENT_PAGE_WINDOW
    if window_size <= 0:
        return DEFAULT_SUPPLEMENT_PAGE_WINDOW
    return window_size


def _supplement_max_scan_pages() -> int:
    raw_value = os.getenv("ROB2_SUPPLEMENT_MAX_SCAN_PAGES", "").strip()
    if not raw_value:
        legacy_value = os.getenv("ROB2_SUPPLEMENT_MAX_PAGES", "").strip()
        raw_value = legacy_value
    if not raw_value:
        return DEFAULT_SUPPLEMENT_MAX_SCAN_PAGES
    try:
        max_pages = int(raw_value)
    except ValueError:
        return DEFAULT_SUPPLEMENT_MAX_SCAN_PAGES
    if max_pages <= 0:
        return DEFAULT_SUPPLEMENT_MAX_SCAN_PAGES
    return max_pages


def _is_page_range_exhausted(error: Exception) -> bool:
    message = str(error).casefold()
    processing_error_markers = (
        "bad_alloc",
        "memory",
        "preprocess failed",
        "conversion failed",
        "failed converting",
        "runtimeerror",
    )
    if any(marker in message for marker in processing_error_markers):
        return False
    exhausted_markers = (
        "page range outside",
        "page range out of range",
        "outside document",
        "exceeds document",
        "no pages",
        "invalid page range",
    )
    return any(marker in message for marker in exhausted_markers)


def _get_supplement_converter():
    global _SUPPLEMENT_CONVERTER
    if _SUPPLEMENT_CONVERTER is not None:
        return _SUPPLEMENT_CONVERTER

    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pipeline_options = PdfPipelineOptions()
    pipeline_options.allow_external_plugins = True
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = False
    pipeline_options.force_backend_text = True
    pipeline_options.layout_batch_size = 1
    pipeline_options.table_batch_size = 1
    pipeline_options.ocr_batch_size = 1
    pipeline_options.queue_max_size = 1
    _SUPPLEMENT_CONVERTER = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        },
    )
    return _SUPPLEMENT_CONVERTER
