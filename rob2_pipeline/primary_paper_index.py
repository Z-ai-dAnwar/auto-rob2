"""Deterministic BM25 index over the primary paper's raw ``full_text``.

ADR-0008. The classifier's evidence packet reached the primary paper only through
``state["evidence"]`` - a stochastic ``paper_evidence_extraction`` LLM summary that
drops decisive sentences on some runs. The raw paper text is in
``state["full_text"]`` but was never searched. This module chunks ``full_text`` into
short passages and wraps them as ``SupplementSegment`` records so the existing
``bm25s`` retrieval machinery (``SupplementIndex``) can search the primary paper
deterministically, the same way supplements are already searched.

Short passages retrieve better than whole sections (measured in the ADR de-risk),
so we split into sentence-grouped passages capped at ``PRIMARY_PASSAGE_MAX_CHARS``.
Passages carry ``document_role="primary"`` and no domain tags: the primary index is
not domain-partitioned, so every signaling question searches the whole paper.
"""

from __future__ import annotations

import re

from rob2_pipeline.supplement_retrieval import SupplementIndex, SupplementSegment

# Short passages retrieve the decisive sentence more reliably than whole sections
# (ADR-0008 de-risk). Grouping sentences up to this cap keeps passages from being
# so tiny that BM25 term statistics degrade, while staying well below a section.
PRIMARY_PASSAGE_MAX_CHARS = 600

PRIMARY_DOCUMENT_ID = "primary"
PRIMARY_DOCUMENT_NAME = "Primary paper full text"

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def primary_paper_passages(
    full_text: str, *, max_chars: int = PRIMARY_PASSAGE_MAX_CHARS
) -> list[str]:
    """Split ``full_text`` into short retrieval passages.

    Paragraphs (blank-line separated) are the outer unit; within a paragraph,
    sentences are greedily packed into passages up to ``max_chars`` so a decisive
    sentence stays with its immediate context without spilling across a section.
    Deterministic: the same ``full_text`` always yields the same passages.
    """
    passages: list[str] = []
    for paragraph in _PARAGRAPH_SPLIT_RE.split(full_text or ""):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        current = ""
        for sentence in _SENTENCE_SPLIT_RE.split(paragraph):
            sentence = sentence.strip()
            if not sentence:
                continue
            if not current:
                current = sentence
            elif len(current) + 1 + len(sentence) <= max_chars:
                current = f"{current} {sentence}"
            else:
                passages.append(current)
                current = sentence
        if current:
            passages.append(current)
    return passages


def primary_paper_segments(full_text: str) -> list[SupplementSegment]:
    """Wrap primary-paper passages as ``SupplementSegment`` records.

    ``document_role="primary"`` so the packet ranker's role preference treats these
    as primary-paper evidence; ``domain_tags=[]`` so the index is not
    domain-partitioned (every SQ searches the whole paper).
    """
    return [
        SupplementSegment(
            segment_id=f"{PRIMARY_DOCUMENT_ID}:passage:{index:04d}",
            document_id=PRIMARY_DOCUMENT_ID,
            document_name=PRIMARY_DOCUMENT_NAME,
            document_role="primary",
            source_path="",
            heading="",
            page_numbers=[],
            domain_tags=[],
            annotation="",
            text=passage,
        )
        for index, passage in enumerate(primary_paper_passages(full_text))
    ]


def build_primary_index(full_text: str) -> SupplementIndex:
    """Build the deterministic BM25 index over the primary paper's ``full_text``.

    Reuses ``SupplementIndex`` (``bm25s``) so retrieval behaves exactly like the
    supplement path. An empty/whitespace ``full_text`` yields an empty index whose
    ``retrieve`` returns no segments.
    """
    return SupplementIndex.from_segments(primary_paper_segments(full_text))
