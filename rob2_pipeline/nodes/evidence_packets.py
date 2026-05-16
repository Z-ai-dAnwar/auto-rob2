"""Build small, SQ-specific evidence packets from retrieved source chunks."""

from __future__ import annotations

import re
from dataclasses import dataclass

from rob2_pipeline.models import format_evidence
from rob2_pipeline.rag_queries import SQ_QUERIES
from rob2_pipeline.state import RoB2State
from rob2_pipeline.types import EvidenceFact, EvidencePacket, PacketSource, RetrievalGrade


@dataclass(frozen=True)
class EvidenceContract:
    sq_id: str
    domain: str
    required_evidence: tuple[str, ...]
    terms: tuple[str, ...]
    fallback_sections: tuple[str, ...] = ()
    needs_denominator: bool = False
    outcome_bound: bool = False
    needs_prespecification: bool = False


CONTRACTS: dict[str, EvidenceContract] = {
    "1.1": EvidenceContract(
        "1.1",
        "d1",
        ("sequence_generation",),
        ("random", "sequence", "computer", "block", "stratif", "minimi", "assign"),
        ("d1_randomization", "methods"),
    ),
    "1.2": EvidenceContract(
        "1.2",
        "d1",
        ("allocation_concealment", "enrolment_timing"),
        ("conceal", "central", "web", "telephone", "pharmacy", "enrol", "assigned", "allocation"),
        ("d1_randomization", "methods"),
    ),
    "1.3": EvidenceContract(
        "1.3",
        "d1",
        ("baseline_balance",),
        ("baseline", "characteristic", "imbalance", "prognostic", "table"),
        ("baseline_table", "results"),
    ),
    "2.1": EvidenceContract("2.1", "d2", ("participant_awareness",), ("blind", "mask", "open-label", "open label", "aware"), ("d2_blinding", "methods")),
    "2.2": EvidenceContract("2.2", "d2", ("personnel_awareness",), ("blind", "mask", "open-label", "investigator", "personnel", "carer"), ("d2_blinding", "methods")),
    "2.3": EvidenceContract("2.3", "d2", ("trial_context_deviations",), ("deviation", "protocol", "amend", "cross-over", "adherence", "standard of care"), ("d2_blinding", "results", "methods")),
    "2.4": EvidenceContract("2.4", "d2", ("deviation_outcome_impact",), ("deviation", "affected", "outcome", "rescue", "benefit", "lack of effect"), ("results", "methods")),
    "2.5": EvidenceContract("2.5", "d2", ("deviation_balance",), ("balanced", "between groups", "arm", "deviation", "adherence"), ("results", "methods")),
    "2.6": EvidenceContract("2.6", "d2", ("analysis_population",), ("intention", "itt", "modified", "per-protocol", "as treated", "randomized"), ("results", "d4_outcome_meas", "methods")),
    "2.7": EvidenceContract("2.7", "d2", ("analysis_failure_impact",), ("excluded", "randomized", "substantial", "impact", "analysis population"), ("results", "methods")),
    "3.1": EvidenceContract(
        "3.1",
        "d3",
        ("randomized_n", "outcome_data_n"),
        ("randomized", "randomised", "outcome data", "missing", "follow-up", "analysed", "analyzed"),
        ("d3_missing_data", "consort_flow", "results"),
        needs_denominator=True,
    ),
    "3.2": EvidenceContract("3.2", "d3", ("missing_bias_evidence",), ("missing", "sensitivity", "imputation", "lost", "withdraw", "reason"), ("d3_missing_data", "results")),
    "3.3": EvidenceContract("3.3", "d3", ("missingness_true_value",), ("missing", "reason", "withdraw", "progression", "toxicity", "lost"), ("d3_missing_data", "results")),
    "3.4": EvidenceContract("3.4", "d3", ("likely_informative_missingness",), ("censor", "sensitivity", "switch", "salvage", "second-line", "dropout"), ("d3_missing_data", "results")),
    "4.1": EvidenceContract("4.1", "d4", ("measurement_method",), ("outcome", "measure", "definition", "endpoint", "instrument", "criteria"), ("d4_outcome_meas", "methods"), outcome_bound=True),
    "4.2": EvidenceContract("4.2", "d4", ("between_group_measurement_difference",), ("differ", "same", "schedule", "assess", "visit", "criteria", "method"), ("d4_outcome_meas", "methods"), outcome_bound=True),
    "4.3": EvidenceContract("4.3", "d4", ("assessor_awareness",), ("assessor", "blind", "mask", "open-label", "adjudicat", "central review"), ("d2_blinding", "d4_outcome_meas"), outcome_bound=True),
    "4.4": EvidenceContract("4.4", "d4", ("assessment_could_be_influenced",), ("judg", "subjective", "symptom", "radiographic", "clinical", "mortality"), ("d4_outcome_meas", "methods"), outcome_bound=True),
    "4.5": EvidenceContract("4.5", "d4", ("assessment_likely_influenced",), ("belief", "influence", "independent", "blinded", "adjudication", "standard"), ("d4_outcome_meas", "d2_blinding"), outcome_bound=True),
    "5.1": EvidenceContract(
        "5.1",
        "d5",
        ("prespecified_analysis_plan",),
        ("registr", "protocol", "sap", "statistical analysis plan", "pre-spec", "prespec", "clinicaltrials", "nct"),
        ("d5_registration", "d4_outcome_meas", "methods"),
        outcome_bound=True,
        needs_prespecification=True,
    ),
    "5.2": EvidenceContract(
        "5.2",
        "d5",
        ("eligible_outcome_measurements", "assessed_outcome_binding"),
        ("primary", "secondary", "endpoint", "outcome", "definition", "time point", "protocol", "registr"),
        ("d5_registration", "d4_outcome_meas", "results"),
        outcome_bound=True,
    ),
    "5.3": EvidenceContract(
        "5.3",
        "d5",
        ("eligible_analyses", "assessed_result_binding"),
        ("analysis", "subgroup", "adjusted", "unadjusted", "sap", "statistical analysis plan", "itt"),
        ("d5_registration", "d4_outcome_meas", "results"),
        outcome_bound=True,
    ),
}


_RESULT_STAT_RE = re.compile(r"\b(?:hr|or|rr|hazard ratio|p\s*=|confidence interval|ci\b|\d+(?:\.\d+)?\s*%)", re.I)
_DENOMINATOR_RE = re.compile(r"\b\d[\d,]*\s*/\s*\d[\d,]*\b|\b\d+(?:\.\d+)?\s*%")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_PRESPEC_TERMS = ("registr", "protocol", "sap", "statistical analysis plan", "pre-spec", "prespec", "nct")
_OUTCOME_ALIASES = {
    "overall survival": ("overall survival", "os", "death", "mortality"),
    "progression-free survival": ("progression-free survival", "progression free survival", "pfs", "progression"),
    "adverse events": ("adverse event", "adverse events", "toxicity", "safety", "grade"),
}


def evidence_packet_builder_node(state: RoB2State) -> RoB2State:
    return build_evidence_packets(state)


def build_evidence_packets(state: RoB2State) -> dict:
    packets: dict[str, EvidencePacket] = {}
    facts: dict[str, list[EvidenceFact]] = {}
    grades: dict[str, RetrievalGrade] = {}
    for sq_id, contract in CONTRACTS.items():
        packet = _build_packet_for_contract(state, contract)
        packets[sq_id] = packet
        facts[sq_id] = packet.get("candidate_facts", [])
        grades[sq_id] = packet.get("packet_grade", _grade_packet(0.0, packet.get("missing_evidence", []), packet.get("negative_flags", [])))
    return {"evidence_packets": packets, "evidence_facts": facts, "packet_grades": grades}


def packet_block_for_domain(evidence_packets: dict[str, EvidencePacket], domain: str, max_chars: int = 6500) -> str:
    parts: list[str] = []
    for sq_id in sorted(sq for sq, packet in evidence_packets.items() if packet.get("domain") == domain):
        packet = evidence_packets[sq_id]
        sources = packet.get("sources", [])
        source_lines = []
        for source in sources[:3]:
            pages = source.get("page_numbers") or []
            page = pages[0] if pages else "?"
            section = source.get("section") or "Unknown"
            text = _compact(source.get("text", ""), 700)
            source_lines.append(f"- page {page}, {section}: {text}")
        missing = ", ".join(packet.get("missing_evidence", [])) or "none"
        flags = ", ".join(packet.get("negative_flags", [])) or "none"
        parts.append(
            "\n".join(
                [
                    f"SQ {sq_id} verified evidence packet",
                    f"Required evidence: {', '.join(packet.get('required_evidence', []))}",
                    f"Missing evidence: {missing}",
                    f"Negative flags: {flags}",
                    *source_lines,
                ]
            )
        )
    return _compact("\n\n".join(parts), max_chars)


def _build_packet_for_contract(state: RoB2State, contract: EvidenceContract) -> EvidencePacket:
    candidates = _candidate_sources(state, contract)
    ranked = sorted(candidates, key=lambda source: (-len(source.get("matched_terms", [])), source.get("score", 1e9)))
    selected = ranked[:3]
    text = "\n\n".join(source.get("text", "") for source in selected if source.get("text"))
    matched = {term for source in selected for term in source.get("matched_terms", [])}
    missing = _missing_evidence(contract, text, matched)
    negative_flags = _negative_flags(state, contract, selected, text)
    confidence = _confidence(contract, selected, missing, negative_flags)
    facts = [_source_to_fact(contract, source, confidence) for source in selected if source.get("text")]
    return EvidencePacket(
        sq_id=contract.sq_id,
        domain=contract.domain,
        required_evidence=list(contract.required_evidence),
        sources=selected,
        candidate_facts=facts,
        text=text,
        retrieval_confidence=confidence,
        missing_evidence=missing,
        negative_flags=negative_flags,
        packet_grade=_grade_packet(confidence, missing, negative_flags),
    )


def _candidate_sources(state: RoB2State, contract: EvidenceContract) -> list[PacketSource]:
    raw_sources = list((state.get("rag_chunk_metadata") or {}).get(contract.domain, []))
    raw_sources.extend(_fallback_sources(state, contract))
    terms = _contract_terms(contract)
    sources: list[PacketSource] = []
    for raw in raw_sources:
        text = str(raw.get("text", "")).strip()
        if not text:
            continue
        matched = _matched_terms(text, terms)
        sources.append(
            PacketSource(
                text=text,
                section=str(raw.get("section", "")),
                page_numbers=list(raw.get("page_numbers") or []),
                score=float(raw.get("score", 1.0)),
                matched_terms=matched,
            )
        )
    return sources


def _fallback_sources(state: RoB2State, contract: EvidenceContract) -> list[dict]:
    evidence = state.get("evidence", {})
    sources = []
    for section in contract.fallback_sections:
        section_evidence = evidence.get(section) if evidence else None
        if not section_evidence:
            continue
        text = format_evidence(section_evidence)
        if text:
            sources.append({"text": text, "section": section, "page_numbers": [], "score": 2.0})
    return sources


def _contract_terms(contract: EvidenceContract) -> tuple[str, ...]:
    query_terms = []
    for query in SQ_QUERIES.get(contract.sq_id, []):
        query_terms.extend(word for word in re.findall(r"[a-z0-9-]+", query.lower()) if len(word) > 4)
    return tuple(dict.fromkeys([*contract.terms, *query_terms]))


def _matched_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    lowered = text.casefold()
    return [term for term in terms if term.casefold() in lowered]


def _missing_evidence(contract: EvidenceContract, text: str, matched: set[str]) -> list[str]:
    missing: list[str] = []
    lowered = text.casefold()
    if not text.strip():
        missing.extend(contract.required_evidence)
    elif not matched:
        missing.extend(contract.required_evidence)
    if contract.needs_denominator and not _DENOMINATOR_RE.search(text):
        missing.append("denominator_or_percentage")
    if contract.needs_prespecification and not any(term in lowered for term in _PRESPEC_TERMS):
        missing.append("protocol_or_registration")
    return list(dict.fromkeys(missing))


def _negative_flags(state: RoB2State, contract: EvidenceContract, selected: list[PacketSource], text: str) -> list[str]:
    flags: list[str] = []
    if contract.outcome_bound and _looks_like_wrong_outcome(state.get("outcome", ""), text):
        flags.append("possible_wrong_outcome_context")
    if any(not source.get("page_numbers") for source in selected):
        flags.append("missing_page_source")
    lowered = text.casefold()
    if contract.domain == "d5" and _RESULT_STAT_RE.search(text) and not any(term in lowered for term in _PRESPEC_TERMS):
        flags.append("results_without_prespecification")
    if text and not selected:
        flags.append("generic_background_only")
    return list(dict.fromkeys(flags))


def _looks_like_wrong_outcome(outcome: str, text: str) -> bool:
    outcome_key = outcome.casefold().strip()
    if not outcome_key or not text:
        return False
    lowered = text.casefold()
    wanted_aliases = _aliases_for_outcome(outcome_key)
    if any(alias in lowered for alias in wanted_aliases):
        return False
    for canonical, aliases in _OUTCOME_ALIASES.items():
        if canonical not in outcome_key and any(alias in lowered for alias in aliases):
            return True
    return False


def _aliases_for_outcome(outcome_key: str) -> tuple[str, ...]:
    for canonical, aliases in _OUTCOME_ALIASES.items():
        if canonical in outcome_key:
            return aliases
    words = tuple(word for word in re.findall(r"[a-z0-9]+", outcome_key) if len(word) > 3)
    return words or (outcome_key,)


def _confidence(contract: EvidenceContract, selected: list[PacketSource], missing: list[str], flags: list[str]) -> float:
    if not selected:
        return 0.0
    matched = {term for source in selected for term in source.get("matched_terms", [])}
    term_score = min(1.0, len(matched) / max(1, min(4, len(_contract_terms(contract)))))
    source_score = min(1.0, len(selected) / 2)
    penalty = 0.2 * len(missing) + 0.15 * len(flags)
    return round(max(0.0, min(1.0, (term_score * 0.7) + (source_score * 0.3) - penalty)), 3)


def _grade_packet(confidence: float, missing: list[str], flags: list[str]) -> RetrievalGrade:
    coverage = 0.0 if missing else 1.0
    return {
        "relevance": confidence,
        "coverage": coverage,
        "missing_evidence": missing,
        "retry_recommended": bool(missing or flags or confidence < 0.35),
    }


def _source_to_fact(contract: EvidenceContract, source: PacketSource, confidence: float) -> EvidenceFact:
    quote = _best_sentence(source.get("text", ""), source.get("matched_terms", []))
    return EvidenceFact(
        fact_type=contract.required_evidence[0] if contract.required_evidence else "evidence",
        domain=contract.domain,
        sq_ids=[contract.sq_id],
        claim=_compact(quote, 240),
        quote=quote,
        source_section=source.get("section", ""),
        page_numbers=source.get("page_numbers", []),
        confidence=confidence,
        support_status="supported" if quote else "missing",
    )


def _best_sentence(text: str, terms: list[str]) -> str:
    sentences = _SENTENCE_SPLIT_RE.split(text.strip())
    for sentence in sentences:
        if any(term.casefold() in sentence.casefold() for term in terms):
            return sentence.strip()
    return sentences[0].strip() if sentences and sentences[0].strip() else ""


def _compact(text: str, max_chars: int) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."
