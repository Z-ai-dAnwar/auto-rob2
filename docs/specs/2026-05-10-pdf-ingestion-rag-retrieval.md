# PDF Ingestion: RAG Retrieval Layer

**Date:** 2026-05-10  
**Status:** Proposed

---

## Context

The current pipeline (spec: `2026-05-10-pdf-ingestion-redesign.md`) replaces regex section-parsing with Docling extraction followed by a single LLM extraction pass that maps content into a `PaperEvidence` model. This has improved domain 1, 3, and 5 accuracy but two problems remain:

1. **Domain 2 and 4 accuracy** — relevant text (outcome measurement details, assessor blinding statements, protocol deviations) often exists in the paper but is scattered across the document rather than under a predictable heading. The LLM extraction pass groups content by heading, so these passages are frequently assigned to the wrong domain field or missed entirely. The result is the LLM answering NI rather than inferring from available evidence.

2. **Token cost** — each domain node receives its full domain evidence field regardless of how much of it is actually relevant to each signaling question. Domain 4 in particular receives the entire `d4_outcome_meas` block for both measurement-method questions (4.1–4.2) and assessor-awareness questions (4.3–4.5), even though these draw on different parts of the text.

The proposed fix adds a **RAG retrieval layer** between the ingest node and the domain assessment nodes. Rather than pre-partitioning the document at extraction time, it builds a per-document chunk index from Docling's structural output and retrieves targeted context at query time — one retrieval per signaling-question group.

---

## Design

### Architecture

```
pdf_ingest_node → rag_retrieval_node → [D1 D2 D3 D4 D5] → overall_judge → report_formatter
```

`pdf_ingest_node` is extended to expose the raw Docling `ConversionResult` alongside `full_text` and `evidence`. The new `rag_retrieval_node` builds a FAISS chunk index from that `ConversionResult` and pre-retrieves 8 context strings, stored in `state["rag_contexts"]` as plain strings. Domain nodes read from `rag_contexts` instead of `evidence` for their prompt context. `evidence` is retained for fields that do not change (abstract, methods, results) and as a fallback when the Docling document is unavailable.

---

### New module: `rob2_pipeline/rag.py`

Three public functions:

```python
def chunk_docling_doc(conv_result) -> list[dict]:
    """
    Walk Docling ConversionResult elements (TEXT, PARAGRAPH, TABLE,
    SECTION_HEADER, LIST_ITEM). Emit chunks of ≤ 2000 chars.
    Each chunk: {"text": str, "section": str, "idx": int}
    - Prefix each chunk with the nearest preceding section header text.
    - TABLE elements converted to markdown and kept as a single chunk.
    - Chunks < 50 chars merged with the next chunk.
    - Chunks > 2000 chars split on sentence boundaries.
    """

def build_index(chunks: list[dict]) -> tuple[faiss.Index, list[dict]]:
    """
    Embed chunks using sentence-transformers/all-MiniLM-L6-v2 (CPU).
    Model is loaded lazily and cached at module level.
    Returns (faiss_flat_cosine_index, chunks).
    """

def retrieve(index, chunks, queries: list[str], top_k: int = 6, cap: int = 5000) -> str:
    """
    For each query string, retrieve top_k chunks by cosine similarity.
    Merge results across queries, deduplicate by chunk idx, sort by score.
    Concatenate chunk texts up to `cap` chars and return as a single string.
    """
```

**Dependencies added to `pyproject.toml` / `requirements.txt`:**
- `sentence-transformers>=3.0`
- `faiss-cpu>=1.8`

`all-MiniLM-L6-v2` (~80 MB) runs on CPU; embedding ~300 chunks takes under 3 seconds on a laptop. No GPU required.

---

### New module: `rob2_pipeline/rag_queries.py`

Pre-defined query strings per retrieval key:

```python
DOMAIN_QUERIES: dict[str, list[str]] = {
    "d1": [
        "allocation sequence randomization random number concealed envelope",
        "allocation concealment sealed envelope central randomization independent",
        "baseline characteristics demographics imbalance groups comparable",
    ],
    "d2_blinding": [
        "participant blinded masked open-label double-blind aware treatment assignment",
        "carer clinician deliverer aware blinded unblinded intervention",
    ],
    "d2_deviations": [
        "protocol deviation adherence crossover non-adherence dropout discontinuation trial context",
        "concomitant medication rescue therapy additional treatment co-intervention",
    ],
    "d2_analysis": [
        "intention to treat per-protocol modified ITT analysis population",
        "excluded participants post-randomization missing data imputation sensitivity analysis",
    ],
    "d3": [
        "lost to follow-up missing data withdrawal dropout CONSORT flow diagram",
        "sensitivity analysis multiple imputation missing outcome completeness",
        "censoring data maturity minimum follow-up event count",
    ],
    "d4_measurement": [
        "outcome measurement instrument assessment tool questionnaire scale definition",
        "primary outcome endpoint measurement method frequency timing schedule",
        "differential measurement different between groups visit diagnostic opportunity",
    ],
    "d4_assessor": [
        "outcome assessor blinded masked open-label aware treatment assignment",
        "independent adjudication central review blinded committee endpoint review",
        "patient reported outcome PRO self-report questionnaire participant",
    ],
    "d5": [
        "trial registration protocol pre-specified primary outcome analysis plan",
        "ClinicalTrials.gov ISRCTN registered protocol amendment statistical analysis plan",
        "reported outcomes selective reporting pre-planned endpoints",
    ],
}
```

---

### New node: `rob2_pipeline/nodes/rag_retrieval.py`

```python
def rag_retrieval_node(state: RoB2State) -> dict:
    """
    Builds a per-document RAG index and retrieves 8 domain context strings.
    Falls back to evidence fields if docling_doc is None.
    Returns {"rag_contexts": dict[str, str]}.
    """
    conv_result = state.get("docling_doc")
    if conv_result is None:
        return {"rag_contexts": _sections_fallback(state["evidence"])}

    chunks = chunk_docling_doc(conv_result)
    index, chunks = build_index(chunks)

    rag_contexts = {
        key: retrieve(index, chunks, queries)
        for key, queries in DOMAIN_QUERIES.items()
    }

    # Augment d3 with censoring context (time-to-event signal is hard to retrieve by embedding)
    censoring = extract_censoring_context(state["full_text"], state.get("outcome", ""))
    if censoring:
        rag_contexts["d3"] = rag_contexts["d3"] + "\n\n" + censoring

    return {"rag_contexts": rag_contexts}
```

`_sections_fallback()` maps the 8 keys to the most relevant `evidence` fields so the pipeline degrades gracefully when Docling is unavailable.

---

### State changes: `rob2_pipeline/state.py`

Add two fields:

```python
docling_doc: Any           # Docling ConversionResult; excluded from JSON_OUTPUT_KEYS
rag_contexts: dict[str, str]  # 8 keys: d1, d2_blinding, d2_deviations, d2_analysis,
                               #         d3, d4_measurement, d4_assessor, d5
```

`docling_doc` is set by `pdf_ingest_node` and consumed by `rag_retrieval_node`; it is not serialized to JSON output. `rag_contexts` is plain text and JSON-serializable but also excluded from `JSON_OUTPUT_KEYS` (internal pipeline routing state).

---

### Graph change: `rob2_pipeline/graph.py`

Insert `rag_retrieval_node` between `pdf_ingest_node` and the parallel domain fan-out:

```
pdf_ingest_node → rct_screener_node → preliminary_info_node → rag_retrieval_node → [D1 D2 D3 D4 D5]
```

`rag_retrieval_node` runs after `preliminary_info_node` so that `state["outcome"]` is available when augmenting `d3` with censoring context.

---

### Domain node changes (`nodes/domain{1–5}.py`)

Each domain node replaces its `evidence[field]` / `format_evidence()` lookups with the corresponding `rag_contexts` key. Prompt format-string variable names stay the same; only the value changes.

| Domain call | Was | Now |
|---|---|---|
| D1 | `format_evidence(evidence["d1_randomization"])` | `rag_contexts["d1"]` |
| D2 SQ 2.1–2.2 | `format_evidence(evidence["d2_blinding"])` | `rag_contexts["d2_blinding"]` |
| D2 SQ 2.3–2.5 | `format_evidence(evidence["d2_blinding"]) + evidence["methods"]` | `rag_contexts["d2_deviations"]` |
| D2 SQ 2.6–2.7 | `format_evidence(evidence["d4_outcome_meas"]) + evidence["results"]` | `rag_contexts["d2_analysis"]` |
| D3 | `format_evidence(evidence["d3_missing_data"]) + censoring_context` | `rag_contexts["d3"]` (already includes censoring) |
| D4 SQ 4.1–4.2 | `format_evidence(evidence["d4_outcome_meas"])` | `rag_contexts["d4_measurement"]` |
| D4 SQ 4.3–4.5 | `format_evidence(evidence["d2_blinding"])` | `rag_contexts["d4_assessor"]` |
| D5 | `format_evidence(evidence["d5_registration"]) + evidence["results"]` | `rag_contexts["d5"]` |

Note: Domain 4 now passes two distinct context strings — one for measurement questions, one for assessor awareness questions — reducing the chance that irrelevant measurement text crowds out assessor-blinding passages.

---

### Extended D4 auto-set logic: `rob2_pipeline/nodes/domain4.py`

The current rule auto-sets SQ 4.3 = Y when `outcome_type == "patient-reported"` and `sq_2_1 ∈ {Y, PY}`. Extend to cover clinician-graded outcomes in open-label trials:

```python
trial_is_open_label = sq_2_1 in ("Y", "PY") or sq_2_2 in ("Y", "PY")

if trial_is_open_label:
    if outcome_type == "patient-reported":
        sq_4_3 = "Y"
        justification = "Participant is the assessor; cannot be blinded to own treatment."
    elif outcome_type in ("clinician-graded", "clinician-composite"):
        sq_4_3 = "PY"
        justification = (
            "In an open-label trial, the clinician grading or adjudicating the outcome "
            "is likely aware of treatment assignment."
        )
    # vital-status and biomarker: no auto-set (inherently objective measurement)
```

This eliminates a class of NIs for clinician-graded outcomes in open-label trials where assessor awareness is structurally implied by trial design.

---

### Files modified

| File | Change |
|---|---|
| `rob2_pipeline/rag.py` | **New** — `chunk_docling_doc()`, `build_index()`, `retrieve()` |
| `rob2_pipeline/rag_queries.py` | **New** — `DOMAIN_QUERIES` dict |
| `rob2_pipeline/nodes/rag_retrieval.py` | **New** — `rag_retrieval_node()` |
| `rob2_pipeline/pdf_ingestion.py` | Expose `ConversionResult` from `_extract_with_docling` |
| `rob2_pipeline/nodes/ingest.py` | Store `docling_doc` in state |
| `rob2_pipeline/state.py` | Add `docling_doc`, `rag_contexts` fields |
| `rob2_pipeline/graph.py` | Insert `rag_retrieval_node` in graph |
| `rob2_pipeline/nodes/domain1.py` | Swap to `rag_contexts["d1"]` |
| `rob2_pipeline/nodes/domain2.py` | Swap to `rag_contexts["d2_*"]` keys |
| `rob2_pipeline/nodes/domain3.py` | Swap to `rag_contexts["d3"]` |
| `rob2_pipeline/nodes/domain4.py` | Swap to `rag_contexts["d4_*"]` keys + extended auto-set |
| `rob2_pipeline/nodes/domain5.py` | Swap to `rag_contexts["d5"]` |
| `tests/test_rag.py` | **New** — unit tests for chunking, indexing, retrieval |
| `tests/test_rag_retrieval_node.py` | **New** — node I/O and fallback tests |
| `tests/test_pdf_ingestion.py` | Add test: `docling_doc` stored in state on success, `None` on fallback |

---

### Verification

1. **Unit tests:** `pytest tests/test_rag.py tests/test_rag_retrieval_node.py tests/test_pdf_ingestion.py`
   - Chunking: correct count and structure from mocked Docling elements
   - Short chunk merging and long chunk splitting
   - Index shape matches chunk count
   - Retrieval: deduplication, cap enforcement, multi-query merge

2. **Pipeline smoke test:** Run on one CHAARTED trial PDF; confirm `rag_contexts` has 8 non-empty keys and D4 no longer returns NI for assessor questions when trial is open-label.

3. **Benchmark:** Run `benchmark.py` on the full benchmark set. Target metrics:
   - D4 NI count per trial: ≤ 2 (down from current average)
   - D2/D4 agreement rate: improvement vs. current baseline
   - D1/D3/D5 agreement rate: stable or improved (no regression)

4. **Token audit:** Check `llm_call_log` in output JSON; total `input_tokens` across all 9 LLM calls should be 50–70% lower than pre-RAG baseline.
