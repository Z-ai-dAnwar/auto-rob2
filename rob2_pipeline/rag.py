import re
from typing import Any

import faiss
import numpy as np

from rob2_pipeline.docling_utils import export_table_markdown, label_name


MAX_CHUNK_CHARS = 2000
MIN_CHUNK_CHARS = 50
_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        _MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _MODEL


def _split_long_text(text: str, limit: int = MAX_CHUNK_CHARS) -> list[str]:
    if len(text) <= limit:
        return [text]
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        if len(sentence) > limit:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(sentence[i : i + limit].strip() for i in range(0, len(sentence), limit))
            continue
        candidate = f"{current} {sentence}".strip()
        if len(candidate) <= limit:
            current = candidate
        else:
            chunks.append(current.strip())
            current = sentence
    if current.strip():
        chunks.append(current.strip())
    return chunks


def _merge_short_chunks(texts: list[str]) -> list[str]:
    merged: list[str] = []
    pending = ""
    for text in texts:
        if pending:
            text = f"{pending}\n\n{text}".strip()
            pending = ""
        if len(text) < MIN_CHUNK_CHARS:
            pending = text
            continue
        merged.append(text)
    if pending:
        if merged and len(merged[-1]) + len(pending) + 2 <= MAX_CHUNK_CHARS:
            merged[-1] = f"{merged[-1]}\n\n{pending}"
        else:
            merged.append(pending)
    return merged


def chunk_docling_doc(conv_result) -> list[dict]:
    doc = getattr(conv_result, "document", conv_result)
    current_section = "Document"
    raw_chunks: list[tuple[str, str]] = []

    iterator = doc.iterate_items() if hasattr(doc, "iterate_items") else []
    for item, _level in iterator:
        item_label_name = label_name(item)
        item_text = (getattr(item, "text", "") or "").strip()
        if item_label_name == "SECTION_HEADER":
            current_section = item_text or current_section
            continue
        if item_label_name == "TABLE":
            table = export_table_markdown(item, doc)
            if table:
                raw_chunks.append((current_section, f"{current_section}\n\n{table}"))
            continue
        if item_label_name in {"TEXT", "PARAGRAPH", "LIST_ITEM"} and item_text:
            raw_chunks.append((current_section, f"{current_section}\n\n{item_text}"))

    grouped: list[tuple[str, str]] = []
    i = 0
    while i < len(raw_chunks):
        section, text = raw_chunks[i]
        if len(text) < MIN_CHUNK_CHARS and i + 1 < len(raw_chunks):
            next_section, next_text = raw_chunks[i + 1]
            if section == next_section:
                grouped.append((section, f"{text}\n\n{next_text}"))
                i += 2
            else:
                grouped.append((section, text))
                i += 1
        else:
            grouped.append((section, text))
            i += 1

    chunks: list[dict] = []
    for section, text in grouped:
        for split_text in _merge_short_chunks(_split_long_text(text)):
            chunks.append({"text": split_text, "section": section, "idx": len(chunks)})
    return chunks


def build_index(chunks: list[dict]) -> tuple[faiss.Index, list[dict]]:
    texts = [chunk["text"] for chunk in chunks]
    if not texts:
        index = faiss.IndexFlatIP(384)
        return index, chunks
    embeddings = _get_model().encode(texts, normalize_embeddings=True)
    vectors = np.asarray(embeddings, dtype="float32")
    if vectors.ndim != 2:
        raise ValueError("Embedding model returned invalid vector shape")
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    return index, chunks


def retrieve(index, chunks, queries: list[str], top_k: int = 6, cap: int = 5000) -> str:
    if not chunks or index.ntotal == 0 or not queries:
        return ""
    query_embeddings = _get_model().encode(queries, normalize_embeddings=True)
    query_vectors = np.asarray(query_embeddings, dtype="float32")
    scores, indices = index.search(query_vectors, min(top_k, len(chunks)))
    best_scores: dict[int, float] = {}
    for score_row, index_row in zip(scores, indices, strict=False):
        for score, chunk_idx in zip(score_row, index_row, strict=False):
            if chunk_idx < 0:
                continue
            best_scores[chunk_idx] = max(best_scores.get(chunk_idx, float("-inf")), float(score))
    parts: list[str] = []
    length = 0
    for chunk_idx, _score in sorted(best_scores.items(), key=lambda item: item[1], reverse=True):
        text = chunks[chunk_idx]["text"].strip()
        separator_len = 2 if parts else 0
        remaining = cap - length - separator_len
        if remaining <= 0:
            break
        if len(text) > remaining:
            text = text[:remaining].rstrip()
        parts.append(text)
        length += len(text) + separator_len
    return "\n\n".join(parts)
