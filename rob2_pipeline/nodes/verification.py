import re

from rob2_pipeline.models import EVIDENCE_SECTION_FIELDS, format_evidence
from rob2_pipeline.state import RoB2State


_BYPASS_QUOTES = {"", "not applicable", "no relevant text found", "not reported"}


def _normalize_text(text: str) -> str:
    text = re.sub(
        r"\([^)]*(?:section|primary evidence|additional retrieved context|results|methods)[^)]*\)",
        "",
        text,
        flags=re.I,
    )
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
    words = [
        word for word in re.findall(r"[a-z0-9]+", normalized_quote) if len(word) > 3
    ]
    if len(words) < 4:
        return False
    hits = sum(1 for word in words if word in source_text)
    return hits / len(words) >= 0.8


def _fragile_sq_issue(sq_id: str, answer: dict) -> str | None:
    value = answer.get("answer", "")
    justification = (answer.get("justification") or "").casefold()
    if (
        sq_id == "3.1"
        and value in ("Y", "PY")
        and not re.search(r"\d+\s*/\s*\d+|\d+(?:\.\d+)?\s*%", justification)
    ):
        return "D3 completeness answer lacks a denominator or percentage calculation."
    if (
        sq_id in ("5.2", "5.3")
        and value in ("Y", "PY")
        and "multiple" not in justification
    ):
        return "D5 selective-reporting answer does not identify multiple eligible measurements or analyses."
    return None


def verify_sq_evidence(state: RoB2State) -> list[dict]:
    source = _source_text(state)
    flags = []
    for sq_id, answer in sorted((state.get("sq_answers") or {}).items()):
        quote = answer.get("quote", "")
        if not quote_is_supported(quote, source):
            flags.append(
                {
                    "sq_id": sq_id,
                    "issue": "quote_not_found_in_source_context",
                    "quote": quote,
                }
            )
        fragile_issue = _fragile_sq_issue(sq_id, answer)
        if fragile_issue:
            flags.append({"sq_id": sq_id, "issue": fragile_issue, "quote": quote})
    flags.extend(verify_packet_evidence(state))
    return flags


def verify_packet_evidence(state: RoB2State) -> list[dict]:
    flags = []
    for sq_id, packet in sorted((state.get("evidence_packets") or {}).items()):
        grade = packet.get("packet_grade") or {}
        missing = grade.get("missing_evidence") or packet.get("missing_evidence") or []
        negative_flags = packet.get("negative_flags") or []
        if grade.get("retry_recommended") or missing or negative_flags:
            details = []
            if missing:
                details.append("missing: " + ", ".join(missing))
            if negative_flags:
                details.append("negative_flags: " + ", ".join(negative_flags))
            flags.append(
                {
                    "sq_id": sq_id,
                    "issue": "packet_verification_failed"
                    + (f" ({'; '.join(details)})" if details else ""),
                    "quote": "",
                }
            )
    return flags


def _verification_actions_from_flags(flags: list[dict]) -> list[dict]:
    actions = []
    for flag in flags:
        issue = flag.get("issue", "")
        if "packet_verification_failed" in issue:
            actions.append(
                {
                    "sq_id": flag.get("sq_id", ""),
                    "action": "retry_packet_or_escalate",
                    "reason": issue,
                }
            )
        elif flag.get("issue") == "quote_not_found_in_source_context":
            actions.append(
                {
                    "sq_id": flag.get("sq_id", ""),
                    "action": "retry_sq_with_verified_packet",
                    "reason": issue,
                }
            )
    return actions


def quote_verifier_node(state: RoB2State) -> RoB2State:
    flags = verify_sq_evidence(state)
    trace = list(state.get("verifier_trace", []))
    actions = _verification_actions_from_flags(flags)
    if flags:
        trace.append(
            {
                "node": "quote_verifier",
                "action": "flag",
                "reason": f"{len(flags)} evidence validation issue(s) found",
            }
        )
    return {
        "evidence_validation_flags": flags,
        "verifier_trace": trace,
        "verification_actions": actions,
    }
