# Design: Docling + LangChain RAG Refactor

**Date:** 2026-05-16

---

## Context

The auto-rob2 pipeline uses Docling for PDF parsing but bypasses the native `langchain-docling` integration. It has a hand-rolled chunker (`chunk_docling_doc` with hardcoded 2000-char splits), custom numpy FAISS indexing, and manual embedding code in `rag.py`. Static per-domain query sets (6 queries per domain) dilute retrieval across unrelated signalling questions. The result is a fragile RAG layer that is harder to maintain and leaves accuracy gains on the table.

This refactor modernises the RAG layer using the official `DoclingLoader` + `HybridChunker` + LangChain FAISS stack, adds metadata-filtered and adaptive retrieval, expands queries to per-SQ granularity, and adds a structured observability channel (`rag_chunk_metadata`) so wrong assessments can be debugged against specific retrieved chunks.

**Goal:** balanced — improve accuracy AND code quality, with no regression on the existing benchmark.

---

## Approach: Targeted RAG Modernization + Observability

Scope is limited to the RAG layer and ingestion node. Graph topology, state reducers (except additions), LLM providers, domain prompt templates, judges, and overall logic are untouched.

---

## Design

### 1. Graph Topology

**Unchanged.** No new nodes. The existing `pdf_ingest_node` absorbs the HybridChunker pass as an internal step.

```
pdf_ingest → rct_screener → preliminary_info → rag_retrieval
  → [D1–D5 parallel] → judges → overall → reporter
```

### 2. `pdf_ingestion.py` — Ingest Node Changes

**Remove PyMuPDF4LLM fallback entirely.**

`extract_full_text()` becomes two-stage only:
- Primary: `DoclingLoader` / `DocumentConverter` (OCR off)
- Fallback: retry with OCR on (`PipelineOptions(do_ocr=True)`)
- Hard failure if both fail — no silent degradation

`pymupdf` and `pymupdf4llm` removed from `pyproject.toml`.

**Add HybridChunker pass.**

After successful Docling conversion, `pdf_ingest_node` calls `_build_docling_chunks(conv_result)` and includes `docling_chunks` in its returned state dict.

```python
# rob2_pipeline/pdf_ingestion.py

from docling.chunking import HybridChunker
from langchain_core.documents import Document

_EMBED_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"

def _build_docling_chunks(conv_result) -> list[Document]:
    chunker = HybridChunker(tokenizer=_EMBED_MODEL_ID)
    docs = []
    for chunk in chunker.chunk(conv_result.document):
        docs.append(
            Document(
                page_content=chunk.text,
                metadata={
                    "section": chunk.meta.headings[0] if chunk.meta.headings else "",
                    "page_numbers": list(chunk.meta.page_numbers),
                    "dl_meta": chunk.meta.export_json_dict(),
                },
            )
        )
    return docs
```

`pdf_ingest_node` adds `{"docling_chunks": chunks}` to its return dict. If conversion fails after OCR retry, `docling_chunks` is `[]` and an error is logged.

### 3. State Schema — `state.py`

Two new channels added to `RoB2State`:

```python
docling_chunks: Annotated[list, lambda _old, new: new]     # last-write; set once by pdf_ingest
rag_chunk_metadata: Annotated[dict, merge_dicts]            # dict-merge; populated by rag_retrieval
```

`docling_chunks` uses last-write (only one node writes it).
`rag_chunk_metadata` uses the same `merge_dicts` reducer as `domain_judgments`.

### 4. `types.py` — New Type

```python
class ChunkMeta(TypedDict, total=False):
    text: str
    section: str
    page_numbers: list[int]
    score: float
```

`LLMCallLogEntry` extended with optional `chunk_sources: list[str]`.

### 5. `rag.py` — Core RAG Rewrite

Replace manual numpy FAISS + `chunk_docling_doc` with LangChain FAISS.

**Embeddings (module-level singleton):**
```python
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

_embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"normalize_embeddings": True},
)
```

**Index construction:**
```python
def build_index(chunks: list[Document]) -> FAISS:
    if not chunks:
        raise ValueError("Cannot build index from empty chunk list")
    return FAISS.from_documents(chunks, _embeddings)
```

**Domain section filters** (for pre-filtering retrieval by section heading):
```python
DOMAIN_SECTION_FILTERS: dict[str, list[str]] = {
    "d1": ["method", "random", "allocat", "participant", "baseline", "consort", "enrol"],
    "d2": ["method", "blind", "mask", "deviat", "protocol", "intervention", "treatment"],
    "d3": ["missing", "censor", "loss", "follow", "withdraw", "dropout", "attrition"],
    "d4": ["outcome", "measur", "assess", "endpoint", "instrument", "adjudicat"],
    "d5": ["registr", "protocol", "trial design", "nct"],
}
```

**Adaptive retrieval:**

Two-phase strategy per domain:
1. Filter `docling_chunks` to chunks whose `metadata["section"]` matches any keyword → build sub-index
2. If filtered results < 3 chunks, fall back to full-index search
3. Aggregate scores across all queries per chunk (best score wins), sort, accumulate to token budget

Token budget: `token_budget=1200` (≈ 4800 chars, replacing hard 5000-char cap). Token estimate: `len(text) // 4`.

**Filtered sub-index construction:**
```python
def build_filtered_index(
    chunks: list[Document],
    keywords: list[str],
) -> FAISS | None:
    filtered = [
        c for c in chunks
        if any(kw in (c.metadata.get("section") or "").lower() for kw in keywords)
    ]
    if len(filtered) < 3:
        return None
    return FAISS.from_documents(filtered, _embeddings)
```

### 6. `rag_queries.py` — Per-SQ Query Sets

Replace `DOMAIN_QUERIES` with `SQ_QUERIES` keyed by SQ ID (e.g. `"1.1"`, `"2.3"`), with 3–5 queries per SQ. A `domain_queries(domain)` helper collects all SQ queries for a given domain.

This replaces the previous 6-query-per-domain approach with ~3–5 queries per signalling question, reducing retrieval dilution across unrelated SQs.

### 7. `nodes/rag_retrieval.py` — Populate Observability Channel

`rag_retrieval_node` populates both:
- `rag_contexts: dict[str, str]` — existing channel, string for domain prompts (unchanged consumer interface)
- `rag_chunk_metadata: dict[str, list[dict]]` — new channel, structured chunk source data

### 8. `nodes/common.py` + `io.py`

- `call_node_llm` accepts optional `chunk_sources: list[str]` and appends it to `LLMCallLogEntry`
- Domain SQ nodes derive `chunk_sources` from `rag_chunk_metadata[domain]` (top 5 sources as `"[page N, Section]"` strings)
- `io.py` emits `rag_sources` as a top-level key in JSON output (omitted from Markdown report)

---

## Files Changed

| File | Action | Summary |
|---|---|---|
| `rob2_pipeline/pdf_ingestion.py` | Modify | Remove PyMuPDF4LLM fallback; add `_build_docling_chunks()` |
| `rob2_pipeline/rag.py` | Rewrite | LangChain FAISS, adaptive retrieval, metadata filters |
| `rob2_pipeline/rag_queries.py` | Rewrite | Per-SQ `SQ_QUERIES` + `domain_queries()` helper |
| `rob2_pipeline/state.py` | Modify | Add `docling_chunks`, `rag_chunk_metadata` channels |
| `rob2_pipeline/types.py` | Modify | Add `ChunkMeta`; extend `LLMCallLogEntry` |
| `rob2_pipeline/nodes/rag_retrieval.py` | Modify | Use new rag.py API; populate `rag_chunk_metadata` |
| `rob2_pipeline/nodes/common.py` | Modify | Accept + log `chunk_sources` |
| `rob2_pipeline/io.py` | Modify | Emit `rag_sources` in JSON output |
| `pyproject.toml` | Modify | Add `langchain-community`, `langchain-huggingface`; remove pymupdf |

**No new files. Graph topology unchanged.**

---

## Verification

1. `pytest` — full suite must pass
2. `benchmark.py` — per-domain accuracy must not regress vs. `outputs/benchmark/benchmark_report.md`
3. `rag_chunk_metadata` in JSON output populated with section headings and page numbers
4. `docling_chunks` non-empty for both OCR and non-OCR PDFs
5. No `pymupdf` references remain in codebase
