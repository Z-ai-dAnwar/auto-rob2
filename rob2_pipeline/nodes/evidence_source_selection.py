"""Select and annotate evidence packet candidate sources."""

from __future__ import annotations

import re

from rob2_pipeline.models import format_evidence
from rob2_pipeline.nodes.evidence_contracts import EvidenceContract, OUTCOME_ALIASES
from rob2_pipeline.rag_queries import SQ_QUERIES
from rob2_pipeline.state import RoB2State
from rob2_pipeline.types import PacketSource


def candidate_sources(
    state: RoB2State, contract: EvidenceContract
) -> list[PacketSource]:
    raw_sources = list((state.get("rag_chunk_metadata") or {}).get(contract.domain, []))
    # Section-text sources are belt-and-suspenders supplementary context for the
    # LLM and run unconditionally alongside any RAG hits. They carry a
    # source_kind="section_text" tag so downstream code (e.g. the verifier) can
    # distinguish them from real RAG chunks, which have page metadata.
    raw_sources.extend(fallback_sources(state, contract))
    terms = contract_terms(contract)
    sources: list[PacketSource] = []
    for raw in raw_sources:
        text = str(raw.get("text", "")).strip()
        if not text:
            continue
        matched = matched_terms(text, terms)
        sources.append(
            PacketSource(
                text=text,
                section=str(raw.get("section", "")),
                page_numbers=list(raw.get("page_numbers") or []),
                score=float(raw.get("score", 1.0)),
                matched_terms=matched,
                source_kind=str(raw.get("source_kind", "rag_chunk")),
            )
        )
    return sources


def fallback_sources(state: RoB2State, contract: EvidenceContract) -> list[dict]:
    evidence = state.get("evidence", {})
    sources = []
    for section in contract.fallback_sections:
        section_evidence = evidence.get(section) if evidence else None
        if not section_evidence:
            continue
        text = format_evidence(section_evidence)
        if text:
            sources.append(
                {
                    "text": text,
                    "section": section,
                    "page_numbers": [],
                    "score": 2.0,
                    "source_kind": "section_text",
                }
            )
    return sources


def contract_terms(contract: EvidenceContract) -> tuple[str, ...]:
    query_terms = []
    for query in SQ_QUERIES.get(contract.sq_id, []):
        query_terms.extend(
            word for word in re.findall(r"[a-z0-9-]+", query.lower()) if len(word) > 4
        )
    return tuple(dict.fromkeys([*contract.terms, *query_terms]))


def matched_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    lowered = text.casefold()
    return [term for term in terms if term.casefold() in lowered]


def looks_like_wrong_outcome(outcome: str, text: str) -> bool:
    outcome_key = outcome.casefold().strip()
    if not outcome_key or not text:
        return False
    lowered = text.casefold()
    wanted_aliases = aliases_for_outcome(outcome_key)
    if any(alias in lowered for alias in wanted_aliases):
        return False
    for canonical, aliases in OUTCOME_ALIASES.items():
        if canonical not in outcome_key and any(alias in lowered for alias in aliases):
            return True
    return False


def aliases_for_outcome(outcome_key: str) -> tuple[str, ...]:
    for canonical, aliases in OUTCOME_ALIASES.items():
        if canonical in outcome_key:
            return aliases
    words = tuple(
        word for word in re.findall(r"[a-z0-9]+", outcome_key) if len(word) > 3
    )
    return words or (outcome_key,)
