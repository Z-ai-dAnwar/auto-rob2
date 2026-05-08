import logging
import os
import re

import pymupdf4llm


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
    "missing_data": ["missing data", "lost to follow", "dropout", "withdrawal", "discontinu"],
    "registration": ["clinicaltrials", "isrctn", "trial registration", "registered", "protocol number"],
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
_DOCLING_CONVERTERS: dict[bool, object] = {}


def extract_full_text(pdf_path: str) -> str:
    try:
        return _normalize_extracted_text(_extract_with_docling(pdf_path))
    except Exception as docling_error:
        try:
            return _normalize_extracted_text(_extract_with_pymupdf4llm(pdf_path))
        except Exception as fallback_error:
            raise RuntimeError(
                f"PDF text extraction failed with Docling and PyMuPDF4LLM for {pdf_path!r}. "
                f"Docling error: {docling_error}. PyMuPDF4LLM error: {fallback_error}."
            ) from fallback_error


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
        raise RuntimeError(f"langchain-docling returned too little text to use with OCR={use_ocr}")
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
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)},
    )
    _DOCLING_CONVERTERS[use_ocr] = converter
    return converter


def _configure_docling_runtime() -> None:
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TQDM_DISABLE", "1")
    logging.getLogger("RapidOCR").setLevel(logging.WARNING)
    logging.getLogger("rapidocr").setLevel(logging.WARNING)


def _extract_with_pymupdf4llm(pdf_path: str) -> str:
    markdown = pymupdf4llm.to_markdown(pdf_path)
    if len(markdown.strip()) < MIN_EXTRACTED_CHARS:
        raise RuntimeError("PyMuPDF4LLM returned too little text to use")
    return markdown


def _normalize_extracted_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\xa0", " ")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


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

    return cap_section("\n\n[... nearby text ...]\n\n".join(windows), keywords=keywords) if windows else ""


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
                    + "; ".join(f"{m} patients" for m in matches[:10]) + "]"
                )
        if extra:
            sections["consort"] = consort + "".join(extra)
    return sections


def parse_sections(full_text: str) -> dict[str, str]:
    sections = {name: "" for name in SECTION_ORDER}
    current_section: str | None = None
    buffers = {name: [] for name in SECTION_ORDER}

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
