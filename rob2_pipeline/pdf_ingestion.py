import re

import pymupdf4llm
from langchain_core.messages import HumanMessage
from lxml import etree

from rob2_pipeline import llm_client


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
MAX_SECTION_CHARS = 6000


def extract_full_text(pdf_path: str) -> str:
    return pymupdf4llm.to_markdown(pdf_path)


def cap_section(
    text: str,
    max_chars: int = MAX_SECTION_CHARS,
    keywords: list[str] | None = None,
) -> str:
    if len(text) <= 8000:
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
    return combined[:max_chars]


def _clean_markdown(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def llm_section_parser(full_text: str, llm) -> dict[str, str]:
    cleaned_full = _clean_markdown(full_text)
    preview = cleaned_full[:20000]
    prompt = f"""You are a text-structure extraction system.

Given the Markdown below, identify the character-offset spans for the canonical sections:
abstract, methods, randomization, blinding, outcomes, analysis, results, missing_data, registration, baseline, consort, supplementary.

Return XML only in this format:
<sections>
  <section name=\"methods\"><start>1204</start><end>3887</end></section>
  ...
</sections>

Rules:
- Spans refer to offsets in the provided Markdown string.
- Use 0-based character offsets.
- Provide only sections you can confidently locate.

Markdown (first 20,000 chars):
"""
    message = HumanMessage(content=prompt + preview)
    try:
        response = llm_client.call_llm(llm, [message], node_name="section_parser")
    except Exception:
        return parse_sections(full_text)

    spans = {}
    try:
        root = etree.fromstring(f"<root>{response}</root>".encode())
        for section in root.findall(".//section"):
            name = section.get("name") or ""
            start = section.findtext("start")
            end = section.findtext("end")
            if name in SECTION_ORDER and start and end:
                spans[name] = (int(start), int(end))
    except Exception:
        return parse_sections(full_text)

    sections = {name: "" for name in SECTION_ORDER}
    for name, (start, end) in spans.items():
        if 0 <= start < end <= len(cleaned_full):
            sections[name] = cap_section(cleaned_full[start:end].strip())

    if not spans:
        return parse_sections(full_text)

    if sections["methods"]:
        if not sections["randomization"]:
            sections["randomization"] = sections["methods"]
        if not sections["blinding"]:
            sections["blinding"] = sections["methods"]
    return sections


def _normalize_heading(line: str) -> str:
    line = line.strip().lower()
    line = re.sub(r"^\d+(?:\.\d+)*\s*", "", line)
    line = re.sub(r"[:.\s]+$", "", line)
    return line


def _detect_heading(line: str) -> str | None:
    stripped = line.strip()
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

    return sections


def section_debug_summary(sections: dict[str, str]) -> dict[str, dict[str, int | bool]]:
    return {
        name: {"detected": bool(text), "chars": len(text)}
        for name, text in sections.items()
    }
