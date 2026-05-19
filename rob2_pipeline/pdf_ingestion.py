import logging
import os
import re
import time
from dataclasses import dataclass
from typing import cast

from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from langchain_core.documents import Document
from lxml import etree  # type: ignore[import-untyped]

from rob2_pipeline.config import build_provider
from rob2_pipeline.docling_utils import export_table_markdown, label_name
from rob2_pipeline.models import (
    EVIDENCE_SECTION_FIELDS,
    PaperEvidence,
    empty_paper_evidence,
)
from rob2_pipeline.trace import append_llm_call
from rob2_pipeline.types import LLMCallLogEntry
from rob2_pipeline.xml_parser import sanitize_stray_lt


SECTION_PATTERNS = {
    "abstract": ["abstract"],
    "methods": [
        "methods",
        "materials and methods",
        "patients and methods",
        "study design",
        "methodology",
    ],
    "randomization": [
        "randomis",
        "randomiz",
        "random allocation",
        "allocation sequence",
        "sequence generation",
    ],
    "blinding": ["blind", "mask", "open-label", "open label", "double-blind"],
    "outcomes": [
        "outcome",
        "endpoint",
        "primary outcome",
        "secondary outcome",
        "efficacy measure",
    ],
    "analysis": [
        "statistical analysis",
        "statistical methods",
        "data analysis",
        "intention-to-treat",
        "per-protocol",
        "analysis population",
    ],
    "results": ["results", "findings"],
    "missing_data": [
        "missing data",
        "lost to follow",
        "dropout",
        "withdrawal",
        "discontinu",
    ],
    "registration": [
        "clinicaltrials",
        "isrctn",
        "trial registration",
        "registered",
        "protocol number",
    ],
    "baseline": ["baseline", "demographic", "characteristics"],
    "consort": [
        "consort",
        "flow diagram",
        "figure 1",
        "participant flow",
        "screened",
        "enrolled",
        "randomized",
        "allocated",
    ],
    "supplementary": ["supplement", "appendix", "online material"],
}

SECTION_ORDER = list(SECTION_PATTERNS)
MAX_SECTION_CHARS = 10000
MIN_EXTRACTED_CHARS = 20
_EMBED_MODEL_ID = "BAAI/bge-small-en-v1.5"
_EMBED_MAX_TOKENS = 256
_TOKENIZER_COUNTING_MAX_LENGTH = 10**9
_DOCLING_CONVERTERS: dict[bool, object] = {}
_CENSORING_PATTERNS = [
    re.compile(r"(?i)\bcensor\w*\b.*\d|\d.*\bcensor\w*\b"),
    re.compile(r"(?i)\bdata[ -]?maturity\b.*\d|\d\s*%\s*data\s*maturity"),
    re.compile(r"(?i)\bdata[ -]?cut(?:off)?\b.*\d|\d.*\bdata[ -]?cut(?:off)?\b"),
    re.compile(
        r"(?i)\bfollow[ -]?up\b.*\bcomplete\b.*\d|\d.*\bfollow[ -]?up\b.*\bcomplete\b"
    ),
    re.compile(r"(?i)\badministratively\s+censored\b"),
    re.compile(r"(?i)\bmedian\s+follow[ -]?up\b.*\d"),
    re.compile(r"(?i)\b\d[\d,]*\s*/\s*\d[\d,]*\s+participants?\b.*\bevents?\b"),
    re.compile(r"(?i)\b\d[\d,]*\s+events?\b.*\d|\d.*\b\d[\d,]*\s+events?\b"),
]


def allow_remote_evidence_extraction() -> bool:
    return os.getenv("ROB2_REMOTE_EVIDENCE_EXTRACTION", "1").strip() not in {
        "0",
        "false",
        "False",
    }


def appears_rct_candidate(text: str) -> bool:
    lowered = text.lower()
    trial_signals = [
        "random",
        "randomized",
        "randomised",
        "assigned",
        "allocation",
        "placebo",
        "double-blind",
    ]
    context_signals = ["trial", "participants", "patients", "phase "]
    return any(signal in lowered for signal in trial_signals) and any(
        signal in lowered for signal in context_signals
    )


PROMPT_PAPER_EXTRACTION = """
You are a clinical trial analyst. Extract the following content from the paper below.
For each section, return all relevant narrative text AND any tables that belong to it.
If content is not present, return empty strings - do not invent content.

<paper>
{paper}
</paper>

Return only XML in this shape:
<evidence>
  <abstract><text></text><tables></tables></abstract>
  <methods><text></text><tables></tables></methods>
  <results><text></text><tables></tables></results>
  <d1_randomization><text>allocation sequence, concealment, baseline balance</text><tables></tables></d1_randomization>
  <d2_blinding><text>masking, open-label status, protocol deviations</text><tables></tables></d2_blinding>
  <d3_missing_data><text>dropout, ITT, missing outcome data</text><tables></tables></d3_missing_data>
  <d4_outcome_meas><text>outcome definitions, measurement, analysis plan</text><tables></tables></d4_outcome_meas>
  <d5_registration><text>registration, protocol, pre-specified endpoints</text><tables></tables></d5_registration>
  <consort_flow><text></text><tables></tables></consort_flow>
  <baseline_table><text></text><tables></tables></baseline_table>
</evidence>
""".strip()

PAPER_EXTRACTION_SYSTEM_MESSAGE = (
    "You are an expert systematic reviewer extracting clinical trial evidence. "
    "Respond only in the XML format specified in the prompt."
)


@dataclass
class DocBlock:
    heading: str | None
    level: int
    text: str
    tables: list[str]
    page_start: int


@dataclass
class DocumentRepr:
    blocks: list[DocBlock]
    full_text: str

    def to_prompt_repr(self) -> str:
        parts = []
        for block in self.blocks:
            heading = block.heading or "Document"
            level = max(1, min(block.level or 1, 6))
            section_parts = [f"{'#' * level} {heading}"]
            if block.text.strip():
                section_parts.append(block.text.strip())
            for table in block.tables:
                if table.strip():
                    section_parts.append(f"[TABLE]\n{table.strip()}\n[/TABLE]")
            parts.append("\n\n".join(section_parts))
        return "\n\n".join(parts) if parts else self.full_text


def extract_full_text(pdf_path: str) -> str:
    return _normalize_extracted_text(_extract_with_docling(pdf_path))


def _extract_with_docling(pdf_path: str) -> str:
    errors = []
    for use_ocr in (False, True):
        try:
            return _extract_with_docling_loader(pdf_path, use_ocr=use_ocr)
        except Exception as error:
            errors.append(f"OCR={use_ocr}: {error}")
    raise RuntimeError("; ".join(errors))


def _extract_with_docling_loader(pdf_path: str, use_ocr: bool) -> str:
    _configure_docling_runtime()

    from langchain_docling import DoclingLoader
    from langchain_docling.loader import ExportType

    loader = DoclingLoader(
        file_path=pdf_path,
        converter=_get_docling_converter(use_ocr=use_ocr),
        export_type=ExportType.MARKDOWN,
    )
    docs = list(loader.lazy_load())
    markdown = "\n\n".join(doc.page_content for doc in docs if doc.page_content)
    if len(markdown.strip()) < MIN_EXTRACTED_CHARS:
        raise RuntimeError(
            f"langchain-docling returned too little text to use with OCR={use_ocr}"
        )
    return markdown


def _get_docling_converter(use_ocr: bool):
    converter = _DOCLING_CONVERTERS.get(use_ocr)
    if converter is not None:
        return converter

    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pipeline_options = PdfPipelineOptions()
    pipeline_options.allow_external_plugins = True
    pipeline_options.do_ocr = use_ocr
    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        },
    )
    _DOCLING_CONVERTERS[use_ocr] = converter
    return converter


def _configure_docling_runtime() -> None:
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TQDM_DISABLE", "1")
    logging.getLogger("RapidOCR").setLevel(logging.WARNING)
    logging.getLogger("rapidocr").setLevel(logging.WARNING)


def _normalize_extracted_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\xa0", " ")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def _build_docling_chunker() -> HybridChunker:
    tokenizer = HuggingFaceTokenizer.from_pretrained(
        _EMBED_MODEL_ID,
        max_tokens=_EMBED_MAX_TOKENS,
        model_max_length=_TOKENIZER_COUNTING_MAX_LENGTH,
    )
    return HybridChunker(tokenizer=tokenizer)


def _build_docling_chunks(conv_result) -> list[Document]:
    chunker = _build_docling_chunker()
    docs: list[Document] = []
    for chunk in chunker.chunk(conv_result.document):
        page_numbers = _chunk_page_numbers(chunk)
        docs.append(
            Document(
                page_content=chunk.text,
                metadata={
                    "section": chunk.meta.headings[0] if chunk.meta.headings else "",
                    "page_numbers": page_numbers,
                    "dl_meta": chunk.meta.export_json_dict(),
                },
            )
        )
    return docs


def _chunk_page_numbers(chunk) -> list[int]:
    direct_pages = getattr(chunk.meta, "page_numbers", None)
    if direct_pages is not None:
        return list(direct_pages)
    pages = set()
    for item in getattr(chunk.meta, "doc_items", []) or []:
        for prov in getattr(item, "prov", []) or []:
            page_no = getattr(prov, "page_no", None)
            if page_no:
                pages.add(int(page_no))
    return sorted(pages)


def _page_no(item) -> int:
    prov = getattr(item, "prov", None) or []
    if prov:
        return int(getattr(prov[0], "page_no", 0) or 0)
    return 0


def _export_doc_markdown(doc) -> str:
    if hasattr(doc, "export_to_markdown"):
        return (doc.export_to_markdown() or "").strip()
    if hasattr(doc, "export_to_text"):
        return (doc.export_to_text() or "").strip()
    return ""


def build_document_repr(doc) -> DocumentRepr:
    blocks: list[DocBlock] = []
    current_heading: str | None = None
    current_level = 0
    current_text: list[str] = []
    current_tables: list[str] = []
    current_page = 0

    def flush() -> None:
        nonlocal current_text, current_tables, current_page
        text = "\n".join(part for part in current_text if part).strip()
        if text or current_tables:
            blocks.append(
                DocBlock(
                    heading=current_heading,
                    level=current_level,
                    text=text,
                    tables=list(current_tables),
                    page_start=current_page,
                )
            )
        current_text = []
        current_tables = []
        current_page = 0

    iterator = doc.iterate_items() if hasattr(doc, "iterate_items") else []
    for item, level in iterator:
        item_label_name = label_name(item)
        item_text = (getattr(item, "text", "") or "").strip()
        if item_label_name == "SECTION_HEADER":
            flush()
            current_heading = item_text or None
            current_level = int(level or 1)
            current_page = _page_no(item)
            continue
        if not current_page:
            current_page = _page_no(item)
        if item_label_name == "TABLE":
            table = export_table_markdown(item, doc)
            if table:
                current_tables.append(table)
            continue
        if (
            item_label_name
            in {"TEXT", "PARAGRAPH", "LIST_ITEM", "TITLE", "CAPTION", "FOOTNOTE"}
            and item_text
        ):
            current_text.append(item_text)

    flush()
    return DocumentRepr(blocks=blocks, full_text=_export_doc_markdown(doc))


def _tables_from_xml(parent) -> list[str]:
    tables_el = parent.find("tables")
    if tables_el is None:
        return []
    child_tables = [
        "".join(table.itertext()).strip() for table in tables_el.findall(".//table")
    ]
    child_tables = [table for table in child_tables if table]
    if child_tables:
        return child_tables
    text = "".join(tables_el.itertext()).strip()
    return [text] if text else []


def _parse_paper_evidence_response(response: str) -> PaperEvidence:
    cleaned = re.sub(r"```xml\s*|\s*```", "", response).strip()
    cleaned = sanitize_stray_lt(cleaned)
    parser = etree.XMLParser(recover=True)
    root = etree.fromstring(f"<root>{cleaned}</root>".encode(), parser=parser)
    evidence = empty_paper_evidence("docling_llm")
    for field in EVIDENCE_SECTION_FIELDS:
        field_el = root.find(f".//{field}")
        if field_el is None:
            continue
        text = (field_el.findtext("text") or "").strip()
        cast(dict[str, object], evidence)[field] = {
            "text": text,
            "tables": _tables_from_xml(field_el),
            "source": "llm_extract",
        }
    return evidence


def extract_paper_evidence(
    doc_repr: DocumentRepr,
) -> tuple[PaperEvidence, list[LLMCallLogEntry]]:
    prompt = PROMPT_PAPER_EXTRACTION.format(paper=doc_repr.to_prompt_repr())
    provider = build_provider()
    start = time.perf_counter()
    response_obj = provider.complete(
        system=PAPER_EXTRACTION_SYSTEM_MESSAGE, user=prompt
    )
    response = response_obj.content
    evidence = _parse_paper_evidence_response(response)
    latency_ms = int((time.perf_counter() - start) * 1000)
    log: list[LLMCallLogEntry] = [
        {
            "node": "paper_evidence_extraction",
            "prompt_length_chars": len(prompt),
            "response_length_chars": len(response),
            "latency_ms": latency_ms,
            "cache_hit": False,
            "model": response_obj.model,
            "input_tokens": response_obj.input_tokens,
            "output_tokens": response_obj.output_tokens,
            "cached": response_obj.cached,
        }
    ]
    append_llm_call(
        node="paper_evidence_extraction",
        system_prompt=PAPER_EXTRACTION_SYSTEM_MESSAGE,
        user_prompt=prompt,
        response=response,
        model=response_obj.model,
        input_tokens=response_obj.input_tokens,
        output_tokens=response_obj.output_tokens,
        cached=response_obj.cached,
        latency_ms=latency_ms,
        cache_hit=False,
        reasoning_content=response_obj.reasoning_content,
    )
    return evidence, log


def paper_evidence_from_sections(
    sections: dict[str, str],
    extraction_method: str = "fallback",
    source: str = "keyword_fallback",
    warnings: list[str] | None = None,
) -> PaperEvidence:
    evidence = empty_paper_evidence(extraction_method)
    mapping = {
        "abstract": ["abstract"],
        "methods": ["methods"],
        "results": ["results"],
        "d1_randomization": ["randomization", "methods"],
        "d2_blinding": ["blinding", "methods"],
        "d3_missing_data": ["missing_data", "results"],
        "d4_outcome_meas": ["outcomes", "analysis", "results"],
        "d5_registration": ["registration"],
        "consort_flow": ["consort"],
        "baseline_table": ["baseline"],
    }
    for field, section_names in mapping.items():
        text = "\n\n".join(
            sections.get(name, "") for name in section_names if sections.get(name, "")
        ).strip()
        cast(dict[str, object], evidence)[field] = {
            "text": cap_section(text) if text else "",
            "tables": [],
            "source": source,
        }
    evidence["warnings"] = warnings or []
    return evidence


def extract_structural_paper_evidence(doc_repr: DocumentRepr) -> PaperEvidence:
    evidence = paper_evidence_from_sections(
        parse_sections(doc_repr.to_prompt_repr() or doc_repr.full_text),
        extraction_method="docling_struct",
        source="docling_struct",
        warnings=[
            "LLM evidence extraction failed; used Docling structural keyword mapping."
        ],
    )
    table_mapping = {
        "baseline_table": SECTION_PATTERNS["baseline"],
        "consort_flow": SECTION_PATTERNS["consort"],
        "results": SECTION_PATTERNS["results"],
        "d4_outcome_meas": SECTION_PATTERNS["outcomes"] + SECTION_PATTERNS["analysis"],
        "d5_registration": SECTION_PATTERNS["registration"],
    }
    for block in doc_repr.blocks:
        searchable = "\n".join([block.heading or "", block.text, *block.tables]).lower()
        for field, keywords in table_mapping.items():
            if block.tables and any(keyword in searchable for keyword in keywords):
                field_evidence = cast(dict[str, object], evidence)[field]
                tables = cast(
                    list[str], cast(dict[str, object], field_evidence)["tables"]
                )
                tables.extend(table for table in block.tables if table not in tables)
    return evidence


def cap_section(
    text: str,
    max_chars: int = MAX_SECTION_CHARS,
    keywords: list[str] | None = None,
) -> str:
    if len(text) <= max_chars:
        return text
    if keywords is None:
        keywords = [
            "random",
            "allocation",
            "conceal",
            "blind",
            "mask",
            "itt",
            "per-protocol",
            "missing",
            "imputation",
            "outcome",
            "endpoint",
            "register",
        ]
    chunk_size = 2000
    step = 1000
    chunks = []
    for start in range(0, len(text), step):
        chunk = text[start : start + chunk_size]
        if not chunk:
            break
        score = sum(chunk.lower().count(keyword) for keyword in keywords)
        chunks.append((score, start, chunk))
        if start + chunk_size >= len(text):
            break
    chunks.sort(key=lambda item: (item[0], -item[1]), reverse=True)
    top_chunks = [chunk for score, _, chunk in chunks if chunk and score > 0][:3]
    if not top_chunks:
        top_chunks = [chunk for _, _, chunk in chunks[:3] if chunk]
    marker = "\n[... truncated ...]\n"
    combined = marker.join(top_chunks)
    truncated = combined[:max_chars]
    return (
        truncated
        + f"\n\n[NOTE: Section truncated at {MAX_SECTION_CHARS} characters. Critical content may be absent.]"
    )


def _normalize_heading(line: str) -> str:
    line = line.strip().lower()
    line = re.sub(r"^#{1,6}\s*", "", line)
    line = line.strip("*_` ")
    line = re.sub(r"^\d+(?:\.\d+)*\s*", "", line)
    line = re.sub(r"[:.\s]+$", "", line)
    return line


def _detect_heading(line: str) -> str | None:
    stripped = line.strip()
    if stripped.startswith("|"):
        return None
    normalized = _normalize_heading(line)
    if not normalized or len(normalized) > 120:
        return None
    if stripped.endswith(".") and len(normalized.split()) > 3:
        return None

    for section, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            compact_normalized = normalized.replace(" ", "")
            compact_pattern = pattern.replace(" ", "")
            if pattern in normalized or compact_pattern in compact_normalized:
                return section
    return None


def _extract_keyword_context(full_text: str, section_name: str) -> str:
    keywords = SECTION_PATTERNS[section_name]
    lines = full_text.splitlines()
    windows = []
    seen_ranges = set()

    for index, line in enumerate(lines):
        lowered = line.lower()
        if not any(keyword in lowered for keyword in keywords):
            continue
        start = max(0, index - 3)
        end = min(len(lines), index + 8)
        window_key = (start, end)
        if window_key in seen_ranges:
            continue
        seen_ranges.add(window_key)
        window = "\n".join(lines[start:end]).strip()
        if window:
            windows.append(window)
        if len(windows) >= 8:
            break

    return (
        cap_section("\n\n[... nearby text ...]\n\n".join(windows), keywords=keywords)
        if windows
        else ""
    )


def _augment_consort_from_results(sections: dict) -> dict:
    """When CONSORT section is reference-only, search results/supplementary for flow numbers."""
    import re

    consort = sections.get("consort", "")
    if len(consort) < 300 and re.search(r"fig(?:ure)?|supplement", consort, re.I):
        pattern = re.compile(
            r"(\d[\d,]*)\s+(?:patients?|participants?|subjects?)\s+"
            r"(?:were\s+)?(?:enrolled|randomized|randomised|allocated|included|"
            r"excluded|withdrew|lost|assigned|eligible|screened)",
            re.I,
        )
        extra = []
        for section_name in ("results", "supplementary", "methods"):
            text = sections.get(section_name, "")
            matches = pattern.findall(text[:5000])
            if matches:
                extra.append(
                    f"\n[Patient flow numbers from {section_name} section: "
                    + "; ".join(f"{m} patients" for m in matches[:10])
                    + "]"
                )
        if extra:
            sections["consort"] = consort + "".join(extra)
    return sections


def _parse_sections_from_docling_document(doc) -> dict[str, str] | None:
    try:
        buffers: dict[str, list[str]] = {name: [] for name in SECTION_ORDER}
        sections = {name: "" for name in SECTION_ORDER}
        current_section: str | None = None

        # Docling 2.x exposes items through iterate_items(); this is more stable across versions
        # than depending directly on doc.texts/doc.body child layouts.
        iterator = doc.iterate_items() if hasattr(doc, "iterate_items") else []

        for item, _ in iterator:
            label = getattr(item, "label", None)
            label_name = (
                getattr(label, "name", str(label)).upper() if label is not None else ""
            )
            item_text = (getattr(item, "text", "") or "").strip()

            if label_name == "SECTION_HEADER":
                detected = _detect_heading(item_text)
                if detected is not None:
                    current_section = detected
                    if item_text:
                        buffers[current_section].append(item_text)
                continue

            if label_name == "TABLE":
                table_text = ""
                if hasattr(item, "export_to_markdown"):
                    try:
                        table_text = item.export_to_markdown(doc=doc)
                    except TypeError:
                        table_text = item.export_to_markdown()
                if table_text and current_section is not None:
                    buffers[current_section].append(table_text)
                lowered_table = table_text.lower()
                if table_text and any(
                    keyword in lowered_table for keyword in SECTION_PATTERNS["baseline"]
                ):
                    buffers["baseline"].append(table_text)
                if table_text and any(
                    keyword in lowered_table for keyword in SECTION_PATTERNS["results"]
                ):
                    buffers["results"].append(table_text)
                continue

            if label_name in {
                "TEXT",
                "PARAGRAPH",
                "LIST_ITEM",
                "TITLE",
                "CAPTION",
                "FOOTNOTE",
            }:
                if current_section is not None and item_text:
                    buffers[current_section].append(item_text)

        for name, lines in buffers.items():
            sections[name] = cap_section("\n".join(lines).strip()) if lines else ""

        if sections["methods"]:
            if not sections["randomization"]:
                sections["randomization"] = sections["methods"]
            if not sections["blinding"]:
                sections["blinding"] = sections["methods"]

        full_text = ""
        if hasattr(doc, "export_to_text"):
            full_text = (doc.export_to_text() or "").strip()
        if not full_text:
            full_text = "\n".join(part for part in sections.values() if part)

        for name in (
            "randomization",
            "blinding",
            "outcomes",
            "analysis",
            "missing_data",
            "registration",
            "baseline",
            "consort",
            "supplementary",
        ):
            if not sections[name]:
                sections[name] = _extract_keyword_context(full_text, name)

        return _augment_consort_from_results(sections)
    except Exception as error:
        logging.warning(
            "Docling structured section parse failed; falling back to text parser: %s",
            error,
        )
        return None


def extract_censoring_context(full_text: str, outcome: str) -> str:
    del outcome  # reserved for future outcome-specific filtering
    lines = full_text.splitlines()
    windows = []
    seen_ranges = set()

    for index, line in enumerate(lines):
        if not line.strip():
            continue
        if not any(pattern.search(line) for pattern in _CENSORING_PATTERNS):
            continue
        start = max(0, index - 3)
        end = min(len(lines), index + 4)
        window_key = (start, end)
        if window_key in seen_ranges:
            continue
        seen_ranges.add(window_key)
        window = "\n".join(lines[start:end]).strip()
        if window:
            windows.append(window)
        if len(windows) >= 10:
            break

    if not windows:
        return ""

    return "\n\n[...]\n\n".join(windows)[:2000]


def parse_sections(full_text: str) -> dict[str, str]:
    sections = {name: "" for name in SECTION_ORDER}
    current_section: str | None = None
    buffers: dict[str, list[str]] = {name: [] for name in SECTION_ORDER}

    for raw_line in full_text.splitlines():
        line = raw_line.strip()
        if not line:
            if current_section is not None:
                buffers[current_section].append("")
            continue

        detected = _detect_heading(line)
        if detected is not None:
            current_section = detected
            buffers[current_section].append(line)
            continue

        if current_section is not None:
            buffers[current_section].append(raw_line)

    for name, lines in buffers.items():
        sections[name] = cap_section("\n".join(lines).strip()) if lines else ""

    if sections["methods"]:
        if not sections["randomization"]:
            sections["randomization"] = sections["methods"]
        if not sections["blinding"]:
            sections["blinding"] = sections["methods"]

    for name in (
        "randomization",
        "blinding",
        "outcomes",
        "analysis",
        "missing_data",
        "registration",
        "baseline",
        "consort",
        "supplementary",
    ):
        if not sections[name]:
            sections[name] = _extract_keyword_context(full_text, name)

    sections = _augment_consort_from_results(sections)

    return sections
