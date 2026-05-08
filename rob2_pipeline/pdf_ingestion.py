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
