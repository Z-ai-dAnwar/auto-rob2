# PDF Ingestion Redesign

**Date:** 2026-05-10  
**Status:** Approved for implementation

---

## Context

The current PDF ingestion component extracts text from clinical trial PDFs and parses it into a fixed 12-key `sections` dict using regex-based heading detection. This approach is brittle: if a paper does not use one of the matched keywords as a heading, the section comes back empty or filled with unrelated content. The 12-key schema also maps to paper headings, not RoB 2 domains — so each domain node re-assembles the context it needs from multiple sections.

The goal of this redesign is to replace the regex-based section detection with a Docling-native structural parse followed by a single LLM extraction call, producing a richer `PaperEvidence` model that maps directly to RoB 2 domains and preserves tables as first-class content.

---

## Design

### Overview

Three stages replace the current single-stage text extraction:

1. **Docling extraction** — unchanged entry point; produces both the full markdown string and a native `DoclingDocument` object.
2. **DocumentRepr building** — walks the `DoclingDocument` tree once via `iterate_items()`, grouping content blocks under their parent heading and collecting tables as structured objects. Produces a clean `DocumentRepr`.
3. **LLM extraction pass** — a single structured LLM call receives `DocumentRepr.to_prompt_repr()` and returns domain-aligned evidence parsed into `PaperEvidence`.

---

### Data Model (`rob2_pipeline/models.py` — new file)

```python
class SectionEvidence(TypedDict):
    text:   str        # narrative prose for this section
    tables: list[str]  # markdown table strings from this section
    source: str        # "llm_extract" | "docling_struct" | "keyword_fallback"

class PaperEvidence(TypedDict):
    # General context used by multiple nodes
    abstract:  SectionEvidence
    methods:   SectionEvidence
    results:   SectionEvidence

    # Domain-aligned evidence (content mapped to RoB 2 domain concerns)
    d1_randomization: SectionEvidence   # sequence generation, concealment, baseline balance
    d2_blinding:      SectionEvidence   # masking details, open-label status, protocol deviations
    d3_missing_data:  SectionEvidence   # dropout, ITT analysis, missing outcome data
    d4_outcome_meas:  SectionEvidence   # outcome definitions, measurement, statistical analysis
    d5_registration:  SectionEvidence   # trial registration, protocol, pre-specified endpoints

    # Structured assets
    consort_flow:      SectionEvidence  # CONSORT flow table or diagram description
    baseline_table:    SectionEvidence  # baseline characteristics table

    # Quality signals
    extraction_method: str        # top-level method: "docling_llm" | "docling_struct" | "fallback"
    warnings:          list[str]  # issues flagged during extraction
```

A helper `format_evidence(ev: SectionEvidence) -> str` combines `text` and `tables` into a prompt-ready string. This is a drop-in replacement for the current `sections.get(key, "")` calls in domain nodes.

---

### Stage 2: DocumentRepr (`rob2_pipeline/pdf_ingestion.py`)

```python
@dataclass
class DocBlock:
    heading:    str | None  # nearest parent heading text (None if before any heading)
    level:      int         # heading depth (0 = no heading, 1–3 = H1/H2/H3)
    text:       str         # paragraph / list text
    tables:     list[str]   # markdown table strings in this block
    page_start: int         # page number for provenance

@dataclass
class DocumentRepr:
    blocks:    list[DocBlock]
    full_text: str           # full markdown (kept for preliminary_info + fallback)

    def to_prompt_repr(self) -> str:
        """Renders blocks as headed sections with explicit [TABLE] markers."""
```

`build_document_repr(doc: DoclingDocument) -> DocumentRepr` replaces `_parse_sections_from_docling_document()`. It walks `doc.iterate_items()` once, tracking the current heading context, and groups `TEXT`/`PARAGRAPH` items under their nearest `SECTION_HEADER` ancestor. `TABLE` items are collected into `DocBlock.tables`.

---

### Stage 3: LLM Extraction Pass (`rob2_pipeline/pdf_ingestion.py`)

`extract_paper_evidence(doc_repr: DocumentRepr, llm_client) -> PaperEvidence`

- Formats the document via `doc_repr.to_prompt_repr()`.
- Calls the LLM (via `call_node_llm()`) with a structured extraction prompt.
- Prompt instructs the LLM to extract each domain-aligned section and return XML with `<text>` and `<tables>` sub-elements per section.
- Response is parsed into `PaperEvidence` using the existing XML parsing infrastructure.
- `source` is set to `"llm_extract"` on success.
- **LLM call pattern:** `extract_paper_evidence` calls `build_provider()` directly (from `rob2_pipeline/config.py`) rather than `call_node_llm`, to avoid coupling a non-node function to the node call pattern. The `pdf_ingest_node` wraps the call and appends the resulting log entry to `state["llm_call_log"]` manually — same log shape as all other nodes.

**Prompt shape:**
```
You are a clinical trial analyst. Extract the following content from the paper below.
For each section, return all relevant narrative text AND any tables that belong to it.
If content is not present, return empty strings — do not invent content.

<paper>
{doc_repr.to_prompt_repr()}
</paper>

<evidence>
  <abstract><text>…</text><tables>…</tables></abstract>
  <methods><text>…</text><tables>…</tables></methods>
  <results><text>…</text><tables>…</tables></results>
  <d1_randomization><text>allocation sequence, concealment, baseline balance</text><tables>…</tables></d1_randomization>
  <d2_blinding><text>masking, open-label status, protocol deviations</text><tables>…</tables></d2_blinding>
  <d3_missing_data><text>dropout, ITT, missing outcome data</text><tables>…</tables></d3_missing_data>
  <d4_outcome_meas><text>outcome definitions, measurement, analysis plan</text><tables>…</tables></d4_outcome_meas>
  <d5_registration><text>registration, protocol, pre-specified endpoints</text><tables>…</tables></d5_registration>
  <consort_flow><text>…</text><tables>…</tables></consort_flow>
  <baseline_table><text>…</text><tables>…</tables></baseline_table>
</evidence>
```

---

### Fallback Chain

```
Docling extract → build_document_repr() → extract_paper_evidence() [LLM]
                                                    ↓ LLM fails
                              Docling structural rules (heading-keyword mapping)
                                                    ↓ Docling fails
                         PyMuPDF4LLM → keyword context extraction (existing code)
```

Each fallback level sets `PaperEvidence.extraction_method` and `PaperEvidence.warnings` accordingly.

---

### State Changes (`rob2_pipeline/state.py`)

- **Remove:** `sections: dict[str, str]`
- **Add:** `evidence: PaperEvidence`
- **Keep:** `full_text: str`

`state_factory.py`: initialize `evidence` as an empty `PaperEvidence` with all fields set to `SectionEvidence(text="", tables=[], source="")`.

---

### Node Changes

**`nodes/ingest.py` (`pdf_ingest_node`):**  
Populate `evidence` instead of `sections`. Call `build_document_repr()` then `extract_paper_evidence()`.

**`nodes/domain{1–5}.py` (5 files):**  
Replace `sections.get(key, "")` with `format_evidence(state["evidence"][field])`. Mapping:

| Old access | New access |
|---|---|
| `sections["randomization"]` | `evidence["d1_randomization"]` |
| `sections["blinding"]` | `evidence["d2_blinding"]` |
| `sections["missing_data"]`, `sections["analysis"]` | `evidence["d3_missing_data"]`, `evidence["d4_outcome_meas"]` |
| `sections["outcomes"]`, `sections["results"]` | `evidence["d4_outcome_meas"]`, `evidence["results"]` |
| `sections["registration"]` | `evidence["d5_registration"]` |
| `sections["consort"]` | `evidence["consort_flow"]` |
| `sections["baseline"]` | `evidence["baseline_table"]` |
| `sections["abstract"]`, `sections["methods"]` | `evidence["abstract"]`, `evidence["methods"]` |

---

### Files Modified

| File | Change |
|---|---|
| `rob2_pipeline/models.py` | **New** — `SectionEvidence`, `PaperEvidence`, `format_evidence()` |
| `rob2_pipeline/pdf_ingestion.py` | Major refactor — `DocBlock`, `DocumentRepr`, `build_document_repr()`, `extract_paper_evidence()`, `PROMPT_PAPER_EXTRACTION` constant; deprecate `parse_sections()` |
| `rob2_pipeline/state.py` | Remove `sections`, add `evidence: PaperEvidence` |
| `rob2_pipeline/state_factory.py` | Initialize `evidence` with empty `PaperEvidence` |
| `rob2_pipeline/nodes/ingest.py` | Populate `evidence` instead of `sections` |
| `rob2_pipeline/nodes/domain1.py` | Update field access |
| `rob2_pipeline/nodes/domain2.py` | Update field access |
| `rob2_pipeline/nodes/domain3.py` | Update field access |
| `rob2_pipeline/nodes/domain4.py` | Update field access |
| `rob2_pipeline/nodes/domain5.py` | Update field access |
| `tests/test_pdf_ingestion.py` | Update existing tests + add tests for `build_document_repr`, `extract_paper_evidence`, fallback chain |

---

### Verification

1. **Unit tests:** All existing tests in `tests/test_pdf_ingestion.py` pass after updating for the new interface. New tests cover `build_document_repr()` with mocked Docling items (SECTION_HEADER, TABLE, TEXT), `extract_paper_evidence()` with mocked LLM response, and the fallback chain.
2. **Integration smoke test:** Run `python main.py` on a sample trial PDF and confirm `evidence` is populated with non-empty domain fields and at least one table extracted.
3. **Benchmark:** Compare `PaperEvidence` domain fields against the old `sections` dict on the benchmark PDFs in `benchmark/` to verify richer content.
4. **Type check:** `mypy rob2_pipeline/` passes with the new TypedDicts.
