import re
from typing import Optional

from lxml import etree


VALID_ANSWERS = {"Y", "PY", "PN", "N", "NI", "NA"}
ANSWER_MAPPING = {
    "YES": "Y",
    "NO": "N",
    "PROBABLY YES": "PY",
    "PROBABLY NO": "PN",
    "NO INFORMATION": "NI",
    "NOT APPLICABLE": "NA",
}


def extract_tag(xml_string: str, tag: str) -> Optional[str]:
    """Extract a single tag value. Regex fallback if lxml fails."""
    try:
        wrapped = f"<root>{xml_string}</root>"
        root = etree.fromstring(wrapped.encode())
        el = root.find(f".//{tag}")
        return el.text.strip() if el is not None and el.text else None
    except Exception:
        match = re.search(rf"<{tag}>(.*?)</{tag}>", xml_string, re.DOTALL)
        return match.group(1).strip() if match else None


def _normalize_answer(answer: str) -> str:
    answer = (answer or "NI").strip().upper()
    if answer in VALID_ANSWERS:
        return answer
    return ANSWER_MAPPING.get(answer, "NI")


def _safe_text(value: Optional[str], default: str = "") -> str:
    return value.strip() if value and value.strip() else default


def _regex_extract_sq(xml_string: str, tag_name: str) -> dict[str, str]:
    block_match = re.search(rf"<{tag_name}>(.*?)(?:</{tag_name}>|$)", xml_string, re.DOTALL)
    if not block_match:
        return {}
    block = block_match.group(1)
    return {
        "answer": extract_tag(block, "answer") or "NI",
        "quote": extract_tag(block, "quote") or "No relevant text found",
        "justification": extract_tag(block, "justification") or "No relevant text found",
        "uncertainty_flag": extract_tag(block, "uncertainty_flag") or "NORMAL",
    }


def parse_sq_response(xml_string: str, sq_ids: list[str]) -> dict[str, dict]:
    """
    Parse a multi-SQ XML response into a dict keyed by SQ ID.

    Returns: {"1.1": {"answer": "Y", "quote": "...", "justification": "...",
                      "uncertainty_flag": "NORMAL"}, ...}
    """
    result = {}
    root = None
    try:
        root = etree.fromstring(f"<root>{xml_string}</root>".encode())
    except Exception:
        root = None

    for sq_id in sq_ids:
        tag_name = f"sq_{sq_id.replace('.', '_')}"
        parsed = None

        if root is not None:
            sq_el = root.find(f".//{tag_name}")
            if sq_el is not None:
                parsed = {
                    "answer": sq_el.findtext("answer") or "NI",
                    "quote": sq_el.findtext("quote") or "No relevant text found",
                    "justification": sq_el.findtext("justification") or "No relevant text found",
                    "uncertainty_flag": sq_el.findtext("uncertainty_flag") or "NORMAL",
                }

        if parsed is None:
            parsed = _regex_extract_sq(xml_string, tag_name)

        answer = _normalize_answer(parsed.get("answer", "NI")) if parsed else "NI"
        quote_default = "Not applicable" if answer == "NA" else "No relevant text found"
        justification_default = "Not applicable" if answer == "NA" else "No relevant text found"

        quote = _safe_text(parsed.get("quote") if parsed else None, quote_default)
        justification = _safe_text(parsed.get("justification") if parsed else None, justification_default)
        if answer == "NA":
            if quote == "No relevant text found":
                quote = "Not applicable"
            if justification == "No relevant text found":
                justification = "Not applicable"

        result[sq_id] = {
            "answer": answer,
            "quote": quote,
            "justification": justification,
            "uncertainty_flag": _safe_text(parsed.get("uncertainty_flag") if parsed else None, "NORMAL").upper(),
        }

    return result
