# Docling + LangChain RAG Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernise the RAG layer by replacing hand-rolled chunking and FAISS with `HybridChunker` + LangChain FAISS, add metadata-filtered and adaptive retrieval, expand to per-SQ query sets, and add a structured observability channel (`rag_chunk_metadata`) — all without regressing benchmark accuracy.

**Architecture:** `pdf_ingest_node` absorbs a new `_build_docling_chunks()` step (HybridChunker on the already-converted Docling document) and stores `docling_chunks: list[Document]` in state. `rag.py` is rewritten around LangChain FAISS with two-phase (filtered → full) adaptive retrieval. The graph topology and all domain prompt/judge code are untouched.

**Tech Stack:** `docling>=2.93.0`, `langchain-docling>=2.0.0`, `langchain-community` (FAISS wrapper), `langchain-huggingface` (HuggingFaceEmbeddings), `faiss-cpu`, `sentence-transformers/all-MiniLM-L6-v2`, `langgraph>=1.1.10`

**Spec:** `docs/specs/2026-05-16-docling-langchain-rag-refactor-design.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `pyproject.toml` | Modify | Add `langchain-community`, `langchain-huggingface`; remove `pymupdf`, `pymupdf4llm` |
| `rob2_pipeline/types.py` | Modify | Add `ChunkMeta` TypedDict; extend `LLMCallLogEntry` with optional `chunk_sources` |
| `rob2_pipeline/state.py` | Modify | Add `docling_chunks` and `rag_chunk_metadata` state channels |
| `rob2_pipeline/rag_queries.py` | Rewrite | Per-SQ `SQ_QUERIES` dict + `domain_queries()` helper |
| `rob2_pipeline/rag.py` | Rewrite | LangChain FAISS index, metadata-filtered sub-index, adaptive retrieval |
| `rob2_pipeline/pdf_ingestion.py` | Modify | Remove PyMuPDF4LLM fallback; add `_build_docling_chunks()` |
| `rob2_pipeline/nodes/rag_retrieval.py` | Modify | Use new `rag.py` API; populate `rag_chunk_metadata` |
| `rob2_pipeline/nodes/common.py` | Modify | Accept + log optional `chunk_sources` in `call_node_llm` |
| `rob2_pipeline/nodes/domain1.py`–`domain5.py` | Modify | Pass `chunk_sources` derived from `rag_chunk_metadata` to `call_node_llm` |
| `rob2_pipeline/io.py` | Modify | Emit `rag_sources` in JSON output |
| `tests/test_rag_queries.py` | Modify | Update for `SQ_QUERIES` / `domain_queries()` structure |
| `tests/test_rag.py` | Rewrite | Tests for new LangChain FAISS API, metadata filter, adaptive retrieval |
| `tests/test_pdf_ingestion.py` | Modify | Remove PyMuPDF4LLM tests; add `_build_docling_chunks` assertions |
| `tests/test_rag_retrieval_node.py` | Modify | Assert `rag_chunk_metadata` populated; mock LangChain FAISS |

---

## Task 1: Update dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update `pyproject.toml` dependencies**

In the `[project] dependencies` list:
- **Remove** any line containing `pymupdf` or `pymupdf4llm`
- **Add** (if not already present):
  ```toml
  "langchain-community>=0.3.0",
  "langchain-huggingface>=0.1.0",
  ```

- [ ] **Step 2: Sync dependencies**

```bash
uv sync
```

Expected: no errors.

- [ ] **Step 3: Verify new imports work**

```bash
python -c "from langchain_community.vectorstores import FAISS; from langchain_huggingface import HuggingFaceEmbeddings; print('OK')"
```
Expected output: `OK`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add langchain-community and langchain-huggingface; remove pymupdf deps"
```

---

## Task 2: Foundation types and state channels

**Files:**
- Modify: `rob2_pipeline/types.py`
- Modify: `rob2_pipeline/state.py`

- [ ] **Step 1: Read current `types.py` and `state.py`**

Read both files to understand existing structures before editing.

- [ ] **Step 2: Add `ChunkMeta` to `types.py`**

Add after the existing `LLMCallLogEntry` definition:

```python
class ChunkMeta(TypedDict, total=False):
    text: str
    section: str
    page_numbers: list[int]
    score: float
```

Also extend `LLMCallLogEntry` with the optional field. Change (or confirm) `LLMCallLogEntry` to use `total=False` and add:

```python
    chunk_sources: list[str]   # ["[page 3, Methods]", "[page 7, Randomization]"]
```

- [ ] **Step 3: Write a type-check test**

Create or add to `tests/test_types.py`:

```python
from rob2_pipeline.types import ChunkMeta, LLMCallLogEntry

def test_chunk_meta_fields():
    m: ChunkMeta = {"text": "hello", "section": "Methods", "page_numbers": [3], "score": 0.9}
    assert m["section"] == "Methods"

def test_llm_call_log_entry_accepts_chunk_sources():
    entry: LLMCallLogEntry = {
        "node": "domain1_sq",
        "model": "gpt-4",
        "input_tokens": 100,
        "output_tokens": 50,
        "chunk_sources": ["[page 3, Methods]"],
    }
    assert entry["chunk_sources"] == ["[page 3, Methods]"]
```

- [ ] **Step 4: Run types test**

```bash
pytest tests/test_types.py -v
```
Expected: PASS (2 tests)

- [ ] **Step 5: Add state channels to `state.py`**

Read `state.py` to find the `RoB2State` TypedDict. Add two new channels, following the same annotation pattern used by existing dict channels (e.g. `domain_judgments`):

```python
docling_chunks: Annotated[list, lambda _old, new: new]       # last-write; set once by pdf_ingest
rag_chunk_metadata: Annotated[dict, merge_dicts]              # dict-merge; same reducer as domain_judgments
```

- [ ] **Step 6: Run existing state/graph tests**

```bash
pytest tests/test_graph.py -v -x
```
Expected: all pass (additions are backward-compatible).

- [ ] **Step 7: Commit**

```bash
git add rob2_pipeline/types.py rob2_pipeline/state.py tests/test_types.py
git commit -m "feat: add ChunkMeta type, chunk_sources log field, docling_chunks and rag_chunk_metadata state channels"
```

---

## Task 3: Rewrite `rag_queries.py`

**Files:**
- Modify: `rob2_pipeline/rag_queries.py`
- Modify: `tests/test_rag_queries.py`

- [ ] **Step 1: Read existing `rag_queries.py` and `tests/test_rag_queries.py`**

- [ ] **Step 2: Write failing tests**

Replace `tests/test_rag_queries.py` with:

```python
from rob2_pipeline.rag_queries import SQ_QUERIES, domain_queries

def test_sq_queries_has_all_domains():
    sq_ids = set(SQ_QUERIES.keys())
    assert {"1.1", "1.2", "1.3"}.issubset(sq_ids)
    assert {"2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7"}.issubset(sq_ids)
    assert {"3.1", "3.2", "3.3", "3.4"}.issubset(sq_ids)
    assert {"4.1", "4.2", "4.3", "4.4", "4.5"}.issubset(sq_ids)
    assert {"5.1", "5.2", "5.3"}.issubset(sq_ids)

def test_sq_queries_each_sq_has_at_least_three_queries():
    for sq_id, queries in SQ_QUERIES.items():
        assert len(queries) >= 3, f"SQ {sq_id} has only {len(queries)} queries"

def test_domain_queries_d1_returns_sq1_queries():
    queries = domain_queries("d1")
    all_sq1 = SQ_QUERIES["1.1"] + SQ_QUERIES["1.2"] + SQ_QUERIES["1.3"]
    assert set(queries) == set(all_sq1)

def test_domain_queries_d2_returns_sq2_queries():
    queries = domain_queries("d2")
    expected = []
    for sq_id in ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7"]:
        expected.extend(SQ_QUERIES[sq_id])
    assert set(queries) == set(expected)

def test_domain_queries_d5_returns_sq5_queries():
    queries = domain_queries("d5")
    expected = SQ_QUERIES["5.1"] + SQ_QUERIES["5.2"] + SQ_QUERIES["5.3"]
    assert set(queries) == set(expected)

def test_domain_queries_returns_list_of_strings():
    for domain in ["d1", "d2", "d3", "d4", "d5"]:
        queries = domain_queries(domain)
        assert isinstance(queries, list)
        assert all(isinstance(q, str) for q in queries)
        assert len(queries) > 0
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
pytest tests/test_rag_queries.py -v
```
Expected: FAIL

- [ ] **Step 4: Rewrite `rag_queries.py`**

Replace the entire file with:

```python
"""Per-signalling-question query sets for RAG retrieval."""

SQ_QUERIES: dict[str, list[str]] = {
    # Domain 1 — Randomization process
    "1.1": [
        "sequence generation method",
        "randomization method computer generated",
        "random number table minimization",
        "allocation sequence generation",
        "how were participants randomized",
    ],
    "1.2": [
        "allocation concealment method",
        "sealed opaque envelopes central randomization",
        "pharmacy controlled allocation",
        "allocation sequence concealed from enrolling clinician",
        "concealment of randomization",
    ],
    "1.3": [
        "baseline imbalance between groups",
        "prognostic factor differences at baseline",
        "table 1 baseline characteristics",
        "chance imbalance randomization groups",
        "baseline covariate balance",
    ],

    # Domain 2 — Deviations from intended interventions
    "2.1": [
        "participants blinded to treatment",
        "patient masking allocation",
        "double blind participants open label",
        "unblinded participants aware of assignment",
        "patient knowledge of treatment allocation",
    ],
    "2.2": [
        "carers or personnel blinded",
        "healthcare provider masking",
        "clinical staff unblinded to treatment",
        "investigators aware of treatment assignment",
        "personnel blinding",
    ],
    "2.3": [
        "unintended deviations from protocol",
        "protocol violations cross-over",
        "contamination between arms",
        "co-interventions applied differentially",
        "adherence to assigned intervention",
    ],
    "2.4": [
        "deviations initiated for beneficial reason",
        "allowed rescue medication deviations",
        "permitted deviations protocol",
        "discontinuation due to lack of effect",
    ],
    "2.5": [
        "intention to treat analysis ITT",
        "modified ITT per-protocol population",
        "as-randomized analysis",
        "all randomized participants included analysis",
        "analysis population definition",
    ],
    "2.6": [
        "statistical analysis plan adherence",
        "analysis method as pre-specified",
        "deviation from planned statistical method",
        "primary analysis method",
    ],
    "2.7": [
        "effect of assignment to intervention",
        "effect of adherence to intervention",
        "complier average causal effect CACE",
        "instrumental variable analysis",
    ],

    # Domain 3 — Missing outcome data
    "3.1": [
        "missing outcome data proportion",
        "loss to follow-up rate",
        "withdrawal dropout attrition rate",
        "number of participants with missing data",
        "proportion missing by arm",
    ],
    "3.2": [
        "reasons for missing outcome data",
        "missing at random assumption",
        "differential missing between groups",
        "reasons for withdrawal by arm",
        "informative censoring",
    ],
    "3.3": [
        "missing data handling method",
        "multiple imputation last observation carried forward",
        "complete case analysis missing data",
        "sensitivity analysis for missing data",
        "statistical method for dropouts",
    ],
    "3.4": [
        "sensitivity analysis missing data tipping point",
        "pattern mixture model",
        "best case worst case scenario analysis",
        "robustness of results to missing data assumptions",
    ],

    # Domain 4 — Measurement of outcome
    "4.1": [
        "outcome assessors blinded",
        "blinded outcome measurement masked assessors",
        "unblinded outcome assessors aware of allocation",
        "knowledge of treatment assignment outcome measurement",
        "assessor blinding",
    ],
    "4.2": [
        "outcome measurement method validated instrument",
        "objective measurement self-reported outcome",
        "patient reported outcome PRO",
        "imaging central review",
        "outcome definition assessment method",
    ],
    "4.3": [
        "differential outcome misclassification between groups",
        "measurement error outcome",
        "systematic bias in outcome measurement",
        "outcome assessment reliability",
    ],
    "4.4": [
        "independent outcome adjudication committee",
        "blinded adjudication committee events",
        "central review adjudication",
        "endpoint committee",
    ],
    "4.5": [
        "composite endpoint definition components",
        "primary endpoint specification",
        "outcome definition protocol",
        "endpoint adjudication criteria",
    ],

    # Domain 5 — Selection of reported result
    "5.1": [
        "trial registration number NCT ISRCTN EudraCT",
        "prospective registration ClinicalTrials.gov",
        "registered before enrollment",
        "trial registry entry",
        "registration date versus start date",
    ],
    "5.2": [
        "registered primary outcome matches reported",
        "primary endpoint consistent with registration",
        "outcome switching from registered protocol",
        "discrepancy between registered and reported outcomes",
        "protocol deviation outcome definition",
    ],
    "5.3": [
        "selective outcome reporting multiple analyses",
        "subgroup analysis pre-specified",
        "data dredging fishing multiple comparisons",
        "unreported outcomes suppressed results",
        "all pre-specified outcomes reported",
    ],
}


def domain_queries(domain: str) -> list[str]:
    """Return all SQ queries for a domain (e.g. 'd1' -> SQs 1.1-1.3)."""
    prefix = domain[1]  # "d1" -> "1", "d2" -> "2", etc.
    return [
        query
        for sq_id, queries in SQ_QUERIES.items()
        if sq_id.startswith(prefix)
        for query in queries
    ]
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_rag_queries.py -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add rob2_pipeline/rag_queries.py tests/test_rag_queries.py
git commit -m "feat: replace DOMAIN_QUERIES with per-SQ SQ_QUERIES and domain_queries() helper"
```

---

## Task 4: Rewrite `rag.py`

**Files:**
- Modify: `rob2_pipeline/rag.py`
- Modify: `tests/test_rag.py`

- [ ] **Step 1: Read existing `rag.py` and `tests/test_rag.py`**

- [ ] **Step 2: Write failing tests**

Replace `tests/test_rag.py` with:

```python
"""Tests for the RAG module (LangChain FAISS-backed)."""
import pytest
from langchain_core.documents import Document
from rob2_pipeline.rag import build_index, build_filtered_index, retrieve_adaptive


def _make_doc(text: str, section: str = "", pages: list[int] | None = None) -> Document:
    return Document(
        page_content=text,
        metadata={"section": section, "page_numbers": pages or []},
    )


@pytest.fixture()
def sample_docs():
    return [
        _make_doc("Patients were randomly allocated using computer-generated numbers.", "Methods", [2]),
        _make_doc("Allocation was concealed using sealed opaque envelopes.", "Methods", [2]),
        _make_doc("Baseline characteristics were balanced between arms.", "Baseline", [3]),
        _make_doc("All participants and personnel were blinded to treatment.", "Methods", [4]),
        _make_doc("Follow-up was complete in 95% of patients.", "Results", [8]),
        _make_doc("The trial was registered at ClinicalTrials.gov NCT12345.", "Registration", [1]),
        _make_doc("Missing data were handled using multiple imputation.", "Statistical Analysis", [5]),
        _make_doc("The primary outcome was overall survival.", "Methods", [2]),
    ]


class TestBuildIndex:
    def test_builds_faiss_index_from_docs(self, sample_docs):
        index = build_index(sample_docs)
        assert index is not None

    def test_raises_on_empty_docs(self):
        with pytest.raises(ValueError, match="empty"):
            build_index([])

    def test_index_is_searchable(self, sample_docs):
        index = build_index(sample_docs)
        results = index.similarity_search("randomization method", k=2)
        assert len(results) == 2
        assert any("random" in r.page_content.lower() for r in results)


class TestBuildFilteredIndex:
    def test_filters_by_section_keyword(self, sample_docs):
        filtered = build_filtered_index(sample_docs, keywords=["method"])
        assert filtered is not None
        results = filtered.similarity_search("randomization", k=10)
        for r in results:
            assert "method" in r.metadata.get("section", "").lower()

    def test_returns_none_when_fewer_than_3_matches(self, sample_docs):
        filtered = build_filtered_index(sample_docs, keywords=["registration"])
        assert filtered is None

    def test_returns_none_on_no_matches(self, sample_docs):
        filtered = build_filtered_index(sample_docs, keywords=["xyznonexistent"])
        assert filtered is None

    def test_returns_index_with_3_or_more_matches(self, sample_docs):
        filtered = build_filtered_index(sample_docs, keywords=["method", "baseline"])
        assert filtered is not None


class TestRetrieveAdaptive:
    def test_returns_text_and_metadata(self, sample_docs):
        index = build_index(sample_docs)
        text, metas = retrieve_adaptive(index, None, ["randomization sequence generation"])
        assert isinstance(text, str)
        assert len(text) > 0
        assert isinstance(metas, list)
        assert len(metas) > 0

    def test_metadata_has_required_fields(self, sample_docs):
        index = build_index(sample_docs)
        _, metas = retrieve_adaptive(index, None, ["randomization"])
        for m in metas:
            assert "text" in m
            assert "section" in m
            assert "page_numbers" in m
            assert "score" in m

    def test_respects_token_budget(self, sample_docs):
        index = build_index(sample_docs)
        text_small, _ = retrieve_adaptive(index, None, ["trial"], token_budget=50)
        text_large, _ = retrieve_adaptive(index, None, ["trial"], token_budget=2000)
        assert len(text_small) <= len(text_large)

    def test_uses_filtered_index_when_provided(self, sample_docs):
        index = build_index(sample_docs)
        filtered = build_filtered_index(sample_docs, keywords=["method"])
        text, metas = retrieve_adaptive(index, filtered, ["randomization"])
        for m in metas:
            assert "method" in m["section"].lower()

    def test_falls_back_to_full_index_when_filtered_is_none(self, sample_docs):
        index = build_index(sample_docs)
        text, metas = retrieve_adaptive(index, None, ["follow-up"])
        assert len(metas) > 0

    def test_deduplicates_results_across_queries(self, sample_docs):
        index = build_index(sample_docs)
        text, metas = retrieve_adaptive(
            index, None,
            ["randomization sequence generation", "random allocation sequence"],
        )
        texts = [m["text"] for m in metas]
        assert len(texts) == len(set(texts)), "Duplicate chunks returned"
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
pytest tests/test_rag.py -v
```
Expected: FAIL

- [ ] **Step 4: Rewrite `rag.py`**

Replace the entire file with:

```python
"""RAG module: LangChain FAISS-backed index, metadata-filtered retrieval, adaptive top-k.

Public API:
    build_index(chunks) -> FAISS
    build_filtered_index(chunks, keywords) -> FAISS | None
    retrieve_adaptive(index, filtered_index, queries, ...) -> tuple[str, list[ChunkMeta]]
    DOMAIN_SECTION_FILTERS: dict[str, list[str]]
"""
from __future__ import annotations

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from rob2_pipeline.types import ChunkMeta

_EMBED_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"

_embeddings = HuggingFaceEmbeddings(
    model_name=_EMBED_MODEL_ID,
    model_kwargs={"normalize_embeddings": True},
)

DOMAIN_SECTION_FILTERS: dict[str, list[str]] = {
    "d1": ["method", "random", "allocat", "participant", "baseline", "consort", "enrol"],
    "d2": ["method", "blind", "mask", "deviat", "protocol", "intervention", "treatment"],
    "d3": ["missing", "censor", "loss", "follow", "withdraw", "dropout", "attrition"],
    "d4": ["outcome", "measur", "assess", "endpoint", "instrument", "adjudicat"],
    "d5": ["registr", "protocol", "trial design", "nct"],
}


def build_index(chunks: list[Document]) -> FAISS:
    """Build a FAISS index from a list of LangChain Documents.

    Raises:
        ValueError: If chunks is empty.
    """
    if not chunks:
        raise ValueError("Cannot build index from empty chunk list")
    return FAISS.from_documents(chunks, _embeddings)


def build_filtered_index(
    chunks: list[Document],
    keywords: list[str],
) -> FAISS | None:
    """Build a sub-index restricted to chunks whose section heading matches any keyword.

    Returns None if fewer than 3 chunks match.
    """
    filtered = [
        c
        for c in chunks
        if any(kw in (c.metadata.get("section") or "").lower() for kw in keywords)
    ]
    if len(filtered) < 3:
        return None
    return FAISS.from_documents(filtered, _embeddings)


def retrieve_adaptive(
    index: FAISS,
    filtered_index: FAISS | None,
    queries: list[str],
    token_budget: int = 1200,
    candidate_k: int = 12,
) -> tuple[str, list[ChunkMeta]]:
    """Two-phase adaptive retrieval.

    Phase 1: Search filtered_index if provided.
    Phase 2: If filtered results < 3 unique chunks, supplement from full index.

    Scores are aggregated per chunk across all queries (best score wins).
    Results are sorted by ascending L2 distance and accumulated to token_budget
    (1 token ≈ 4 chars).
    """
    scores: dict[str, float] = {}
    docs_map: dict[str, Document] = {}

    def _search(idx: FAISS) -> None:
        for query in queries:
            for doc, score in idx.similarity_search_with_score(query, k=candidate_k):
                key = doc.page_content[:120]
                if key not in scores or score < scores[key]:
                    scores[key] = score
                    docs_map[key] = doc

    search_idx = filtered_index if filtered_index is not None else index
    _search(search_idx)

    if filtered_index is not None and len(docs_map) < 3:
        _search(index)

    sorted_keys = sorted(scores.keys(), key=lambda k: scores[k])

    result_texts: list[str] = []
    result_metas: list[ChunkMeta] = []
    total_tokens = 0

    for key in sorted_keys:
        doc = docs_map[key]
        chunk_tokens = max(1, len(doc.page_content) // 4)
        if total_tokens + chunk_tokens > token_budget:
            break
        total_tokens += chunk_tokens
        result_texts.append(doc.page_content)
        result_metas.append(
            ChunkMeta(
                text=doc.page_content,
                section=doc.metadata.get("section", ""),
                page_numbers=doc.metadata.get("page_numbers", []),
                score=float(scores[key]),
            )
        )

    return "\n\n".join(result_texts), result_metas
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_rag.py -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add rob2_pipeline/rag.py tests/test_rag.py
git commit -m "feat: rewrite rag.py with LangChain FAISS, metadata-filtered retrieval, adaptive top-k"
```

---

## Task 5: Update `pdf_ingestion.py`

**Files:**
- Modify: `rob2_pipeline/pdf_ingestion.py`
- Modify: `tests/test_pdf_ingestion.py`

- [ ] **Step 1: Read `pdf_ingestion.py` and `tests/test_pdf_ingestion.py`**

Identify: where PyMuPDF4LLM is imported and called; where the `ConversionResult` is available; what `pdf_ingest_node` currently returns; all tests that test PyMuPDF4LLM fallback behavior.

- [ ] **Step 2: Write new tests for `_build_docling_chunks`**

Add to `tests/test_pdf_ingestion.py` (remove any tests that test PyMuPDF4LLM fallback):

```python
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document
from rob2_pipeline.pdf_ingestion import _build_docling_chunks


def _make_mock_chunk(text: str, headings: list[str], pages: list[int]):
    chunk = MagicMock()
    chunk.text = text
    chunk.meta.headings = headings
    chunk.meta.page_numbers = pages
    chunk.meta.export_json_dict.return_value = {"headings": headings, "page_numbers": pages}
    return chunk


def test_build_docling_chunks_returns_langchain_documents():
    mock_conv = MagicMock()
    mock_chunks = [
        _make_mock_chunk("Patients were randomly allocated.", ["Methods"], [2]),
        _make_mock_chunk("Allocation was concealed.", ["Methods"], [2]),
        _make_mock_chunk("Baseline characteristics.", ["Baseline"], [3]),
    ]
    with patch("rob2_pipeline.pdf_ingestion.HybridChunker") as MockChunker:
        MockChunker.return_value.chunk.return_value = mock_chunks
        result = _build_docling_chunks(mock_conv)
    assert len(result) == 3
    assert all(isinstance(d, Document) for d in result)


def test_build_docling_chunks_preserves_section_metadata():
    mock_conv = MagicMock()
    mock_chunks = [_make_mock_chunk("Text about randomization.", ["Methods"], [2])]
    with patch("rob2_pipeline.pdf_ingestion.HybridChunker") as MockChunker:
        MockChunker.return_value.chunk.return_value = mock_chunks
        result = _build_docling_chunks(mock_conv)
    assert result[0].metadata["section"] == "Methods"
    assert result[0].metadata["page_numbers"] == [2]


def test_build_docling_chunks_handles_no_headings():
    mock_conv = MagicMock()
    mock_chunks = [_make_mock_chunk("Plain text.", [], [1])]
    with patch("rob2_pipeline.pdf_ingestion.HybridChunker") as MockChunker:
        MockChunker.return_value.chunk.return_value = mock_chunks
        result = _build_docling_chunks(mock_conv)
    assert result[0].metadata["section"] == ""


def test_build_docling_chunks_returns_empty_list_on_no_chunks():
    mock_conv = MagicMock()
    with patch("rob2_pipeline.pdf_ingestion.HybridChunker") as MockChunker:
        MockChunker.return_value.chunk.return_value = []
        result = _build_docling_chunks(mock_conv)
    assert result == []
```

- [ ] **Step 3: Run new tests to confirm they fail**

```bash
pytest tests/test_pdf_ingestion.py::test_build_docling_chunks_returns_langchain_documents -v
```
Expected: FAIL

- [ ] **Step 4: Update `pdf_ingestion.py`**

**a)** Remove any `import pymupdf4llm` or `import pymupdf` lines. Remove the PyMuPDF4LLM fallback branch in `extract_full_text()`.

**b)** Add at the top of the file:

```python
from docling.chunking import HybridChunker
from langchain_core.documents import Document

_EMBED_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
```

**c)** Add the function:

```python
def _build_docling_chunks(conv_result) -> list[Document]:
    """Convert a Docling ConversionResult to LangChain Documents via HybridChunker."""
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

**d)** In `pdf_ingest_node`, after successful Docling conversion, add:

```python
docling_chunks = _build_docling_chunks(conv_result) if conv_result is not None else []
```

Include `"docling_chunks": docling_chunks` in the returned state dict.

- [ ] **Step 5: Run all pdf_ingestion tests**

```bash
pytest tests/test_pdf_ingestion.py -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add rob2_pipeline/pdf_ingestion.py tests/test_pdf_ingestion.py
git commit -m "feat: remove pymupdf4llm fallback; add _build_docling_chunks via HybridChunker"
```

---

## Task 6: Update `nodes/rag_retrieval.py`

**Files:**
- Modify: `rob2_pipeline/nodes/rag_retrieval.py`
- Modify: `tests/test_rag_retrieval_node.py`

- [ ] **Step 1: Read `nodes/rag_retrieval.py` and `tests/test_rag_retrieval_node.py`**

Understand how the node currently calls the old `build_index`/`retrieve` and what fallback logic exists.

- [ ] **Step 2: Write updated tests**

Replace `tests/test_rag_retrieval_node.py` with:

```python
"""Tests for rag_retrieval_node with new LangChain FAISS API."""
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document
from rob2_pipeline.types import ChunkMeta


def _make_doc(text: str, section: str = "Methods") -> Document:
    return Document(page_content=text, metadata={"section": section, "page_numbers": [1]})


def _base_state(docling_chunks):
    return {"docling_chunks": docling_chunks, "full_text": "sample", "evidence": {}, "errors": []}


def test_rag_retrieval_node_populates_rag_contexts():
    from rob2_pipeline.nodes.rag_retrieval import rag_retrieval_node
    chunks = [_make_doc(f"Chunk {i} about randomization.") for i in range(10)]
    with patch("rob2_pipeline.nodes.rag_retrieval.build_index") as mock_build, \
         patch("rob2_pipeline.nodes.rag_retrieval.build_filtered_index") as mock_filtered, \
         patch("rob2_pipeline.nodes.rag_retrieval.retrieve_adaptive") as mock_retrieve:
        mock_build.return_value = MagicMock()
        mock_filtered.return_value = None
        mock_retrieve.return_value = (
            "Retrieved text.",
            [ChunkMeta(text="Retrieved text.", section="Methods", page_numbers=[2], score=0.9)],
        )
        result = rag_retrieval_node(_base_state(chunks))
    assert "rag_contexts" in result
    for domain in ["d1", "d2", "d3", "d4", "d5"]:
        assert domain in result["rag_contexts"]
        assert isinstance(result["rag_contexts"][domain], str)


def test_rag_retrieval_node_populates_rag_chunk_metadata():
    from rob2_pipeline.nodes.rag_retrieval import rag_retrieval_node
    chunks = [_make_doc(f"Chunk {i}.") for i in range(10)]
    with patch("rob2_pipeline.nodes.rag_retrieval.build_index") as mock_build, \
         patch("rob2_pipeline.nodes.rag_retrieval.build_filtered_index") as mock_filtered, \
         patch("rob2_pipeline.nodes.rag_retrieval.retrieve_adaptive") as mock_retrieve:
        mock_build.return_value = MagicMock()
        mock_filtered.return_value = None
        mock_retrieve.return_value = (
            "Some text.",
            [ChunkMeta(text="Some text.", section="Methods", page_numbers=[3], score=0.85)],
        )
        result = rag_retrieval_node(_base_state(chunks))
    assert "rag_chunk_metadata" in result
    for domain in ["d1", "d2", "d3", "d4", "d5"]:
        metas = result["rag_chunk_metadata"][domain]
        assert isinstance(metas, list)
        assert len(metas) > 0
        assert "section" in metas[0]
        assert "page_numbers" in metas[0]
        assert "score" in metas[0]


def test_rag_retrieval_node_falls_back_when_no_chunks():
    from rob2_pipeline.nodes.rag_retrieval import rag_retrieval_node
    result = rag_retrieval_node(_base_state([]))
    assert "rag_contexts" in result
    if "rag_chunk_metadata" in result:
        for domain in ["d1", "d2", "d3", "d4", "d5"]:
            assert result["rag_chunk_metadata"].get(domain, []) == []
```

- [ ] **Step 3: Run tests to confirm failures**

```bash
pytest tests/test_rag_retrieval_node.py -v
```
Expected: some FAIL

- [ ] **Step 4: Update `nodes/rag_retrieval.py`**

Replace imports at the top:

```python
from rob2_pipeline.rag import (
    build_index,
    build_filtered_index,
    retrieve_adaptive,
    DOMAIN_SECTION_FILTERS,
)
from rob2_pipeline.rag_queries import domain_queries
```

Replace the main body of `rag_retrieval_node`:

```python
def rag_retrieval_node(state: RoB2State) -> dict:
    chunks = state.get("docling_chunks") or []

    if not chunks:
        return _fallback_rag(state)  # keep existing fallback logic unchanged

    index = build_index(chunks)
    rag_contexts: dict[str, str] = {}
    rag_chunk_metadata: dict[str, list[dict]] = {}

    for domain in ["d1", "d2", "d3", "d4", "d5"]:
        keywords = DOMAIN_SECTION_FILTERS.get(domain, [])
        filtered_index = build_filtered_index(chunks, keywords)
        queries = domain_queries(domain)
        text, metas = retrieve_adaptive(index, filtered_index, queries)
        rag_contexts[domain] = text
        rag_chunk_metadata[domain] = [dict(m) for m in metas]

    return {"rag_contexts": rag_contexts, "rag_chunk_metadata": rag_chunk_metadata}
```

Keep the existing `_fallback_rag` function (or inline fallback) intact — only remove old index/retrieve calls in the non-fallback path.

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_rag_retrieval_node.py -v
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add rob2_pipeline/nodes/rag_retrieval.py tests/test_rag_retrieval_node.py
git commit -m "feat: update rag_retrieval_node to use LangChain FAISS API and populate rag_chunk_metadata"
```

---

## Task 7: Update `nodes/common.py` and `io.py`

**Files:**
- Modify: `rob2_pipeline/nodes/common.py`
- Modify: `rob2_pipeline/nodes/domain1.py` through `domain5.py`
- Modify: `rob2_pipeline/io.py`

- [ ] **Step 1: Read `nodes/common.py`, `nodes/domain1.py`, and `io.py`**

Find:
1. The `call_node_llm` function signature and where it builds log entry dicts
2. How each domain SQ node calls `call_node_llm`
3. Where `io.py` constructs the JSON output dict

- [ ] **Step 2: Update `call_node_llm` in `nodes/common.py`**

Add `chunk_sources: list[str] | None = None` as a trailing parameter. When building the log entry, add:

```python
if chunk_sources:
    log_entry["chunk_sources"] = chunk_sources
```

- [ ] **Step 3: Update each domain SQ node (`domain1.py`–`domain5.py`)**

In each file, before calling `call_node_llm`, derive `chunk_sources`:

```python
# domain1.py — use "d1"; domain2.py — use "d2"; etc.
domain_metas = state.get("rag_chunk_metadata", {}).get("d1", [])
chunk_sources = [
    f"[page {m['page_numbers'][0] if m.get('page_numbers') else '?'}, {m.get('section', 'Unknown')}]"
    for m in domain_metas[:5]
]
```

Pass `chunk_sources=chunk_sources` to `call_node_llm`.

- [ ] **Step 4: Update `io.py`**

Find the JSON output dict construction. Add:

```python
"rag_sources": state.get("rag_chunk_metadata", {}),
```

as a top-level key in the output dict.

- [ ] **Step 5: Run full test suite**

```bash
pytest -v -x
```
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add rob2_pipeline/nodes/common.py rob2_pipeline/nodes/domain1.py rob2_pipeline/nodes/domain2.py rob2_pipeline/nodes/domain3.py rob2_pipeline/nodes/domain4.py rob2_pipeline/nodes/domain5.py rob2_pipeline/io.py
git commit -m "feat: add chunk_sources to LLM call log entries and rag_sources to JSON output"
```

---

## Task 8: Final validation

- [ ] **Step 1: Run full test suite**

```bash
pytest -v
```
Expected: all tests PASS.

- [ ] **Step 2: Verify no pymupdf references remain**

```bash
grep -r "pymupdf" rob2_pipeline/ tests/
```
Expected: no output.

- [ ] **Step 3: Verify `docling_chunks` is populated on a sample PDF**

```bash
python -c "
from rob2_pipeline.pipeline import run_pipeline
import glob, os
pdfs = glob.glob('inputs/benchmark/**/*.pdf', recursive=True)
if not pdfs:
    print('No benchmark PDFs found')
else:
    result = run_pipeline(pdfs[0])
    chunks = result.get('docling_chunks', [])
    print(f'Chunks: {len(chunks)}')
    if chunks:
        print(f'First chunk section: {chunks[0].metadata[\"section\"]}')
        print(f'First chunk pages: {chunks[0].metadata[\"page_numbers\"]}')
"
```
Expected: `Chunks: N` where N > 0; non-empty section and page_numbers.

- [ ] **Step 4: Inspect `rag_sources` in JSON output**

After Step 3 produces a JSON output file:

```bash
python -c "
import json, glob
files = sorted(glob.glob('outputs/**/*.json', recursive=True))
if files:
    data = json.load(open(files[-1]))
    sources = data.get('rag_sources', {})
    print('Domains with sources:', list(sources.keys()))
    d1 = sources.get('d1', [])
    if d1:
        print('D1 first chunk section:', d1[0].get('section'))
        print('D1 first chunk pages:', d1[0].get('page_numbers'))
"
```
Expected: all 5 domains present with section and page_numbers populated.

- [ ] **Step 5: Run benchmark**

```bash
python benchmark.py --outcome-map <TRIAL>:<OUTCOME_CODE>
```
Use the same trials as the existing baseline in `outputs/benchmark/`. Compare per-domain accuracy against `outputs/benchmark/benchmark_report.md`.

Expected: no regression on any domain.
