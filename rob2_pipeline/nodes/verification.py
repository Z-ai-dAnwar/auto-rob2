import re

from rob2_pipeline.models import EVIDENCE_SECTION_FIELDS, format_evidence
from rob2_pipeline.state import RoB2State


_BYPASS_QUOTES = {"", "not applicable", "no relevant text found", "not reported"}


def _normalize_text(text: str) -> str:
    text = re.sub(r"\([^)]*(?:section|primary evidence|additional retrieved context|results|methods)[^)]*\)", "", text, flags=re.I)
    text = text.strip().strip('"').strip("'")
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def _source_text(state: RoB2State) -> str:
    evidence = state.get("evidence", {})
    parts = [state.get("full_text", "")]
    for field in EVIDENCE_SECTION_FIELDS:
        section = evidence.get(field) if evidence else None
        if section:
            parts.append(format_evidence(section))
    parts.extend((state.get("rag_contexts") or {}).values())
    return _normalize_text("\n\n".join(part for part in parts if part))


def quote_is_supported(quote: str, source_text: str) -> bool:
    normalized_quote = _normalize_text(quote)
    if normalized_quote in _BYPASS_QUOTES:
        return True
    if normalized_quote in source_text:
        return True
    words = [word for word in re.findall(r"[a-z0-9]+", normalized_quote) if len(word) > 3]
    if len(words) < 4:
        return False
    hits = sum(1 for word in words if word in source_text)
    return hits / len(words) >= 0.8


def _fragile_sq_issue(sq_id: str, answer: dict) -> str | None:
    value = answer.get("answer", "")
    justification = (answer.get("justification") or "").casefold()
    if sq_id == "3.1" and value in ("Y", "PY") and not re.search(r"\d+\s*/\s*\d+|\d+(?:\.\d+)?\s*%", justification):
        return "D3 completeness answer lacks a denominator or percentage calculation."
    if sq_id in ("5.2", "5.3") and value in ("Y", "PY") and "multiple" not in justification:
        return "D5 selective-reporting answer does not identify multiple eligible measurements or analyses."
    return None


def verify_sq_evidence(state: RoB2State) -> list[dict]:
    source = _source_text(state)
    flags = []
    for sq_id, answer in sorted((state.get("sq_answers") or {}).items()):
        quote = answer.get("quote", "")
        if not quote_is_supported(quote, source):
            flags.append({"sq_id": sq_id, "issue": "quote_not_found_in_source_context", "quote": quote})
        fragile_issue = _fragile_sq_issue(sq_id, answer)
        if fragile_issue:
            flags.append({"sq_id": sq_id, "issue": fragile_issue, "quote": quote})
    return flags


def quote_verifier_node(state: RoB2State) -> RoB2State:
    flags = verify_sq_evidence(state)
    trace = list(state.get("verifier_trace", []))
    if flags:
        trace.append(
            {
                "node": "quote_verifier",
                "action": "flag",
                "reason": f"{len(flags)} evidence validation issue(s) found",
            }
        )
    return {"evidence_validation_flags": flags, "verifier_trace": trace}
