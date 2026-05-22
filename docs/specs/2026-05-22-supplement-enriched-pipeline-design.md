# Design: Supplement-Enriched Evidence Pipeline

**Date:** 2026-05-22

---

## Context

The current pipeline accepts one study PDF, extracts primary-paper evidence, enriches trial metadata from ClinicalTrials.gov, retrieves domain-specific context from Docling chunks, builds signaling-question evidence packets, and computes deterministic RoB 2 judgments.

Benchmark supplements now exist under `inputs/benchmark/supplement/<TRIAL>/`. These include protocols, appendices, disclosures, data-sharing statements, and miscellaneous journal files. Standard RoB 2 review practice requires checking these files, but they are too large and heterogeneous to concatenate into the main prompt or merge blindly into primary-paper evidence.

The design goal is to let supplements improve evidence packets without polluting the main article representation or overloading prompts.

---

## Goals

- Preserve current primary-PDF behavior when no supplements are provided.
- Accept an arbitrary number of optional supplementary PDFs per study.
- Keep `full_text` and `evidence` anchored to the main article.
- Add supplement text only through provenance-tagged retrieval and packet sources.
- Make every retrieved source auditable by document name, document role, page, section, and source kind.
- Let benchmark runs opt into supplements without changing primary-only benchmark baselines.
- Handle missing or failed optional supplements without failing the assessment unless explicitly required.

## Non-Goals

- Do not build a full manifest-based benchmark reorganization in the first implementation.
- Do not run remote full-document LLM evidence extraction over every supplement.
- Do not make supplements influence RCT screening or trial identity extraction in the first pass.
- Do not let supplement summaries directly set signaling-question answers or final judgments.

---

## Recommended Approach

Use a hybrid design:

1. Add optional supplement paths to the assessment and benchmark interfaces.
2. Parse supplements through the existing Docling chunking path.
3. Classify each supplement with lightweight deterministic triage.
4. Append supplement chunks to the existing RAG corpus with mandatory provenance metadata.
5. Extend packet source ranking so high-value source roles, especially protocols and SAP-like documents, are prioritized for the right domains.
6. Add ClinicalTrials.gov as structured packet candidates with explicit `source_kind="ctgov"`.

This keeps implementation close to the existing architecture while making source provenance and source role explicit enough for RoB 2 auditability.

---

## Architecture

### Graph Topology

The graph topology does not need a new public branch. Supplement ingestion can be absorbed inside `pdf_ingest_node`, because that node already owns Docling conversion and emits `docling_chunks`.

Current:

```text
pdf_ingest
  -> rct_screener
  -> preliminary_info
  -> outcome_resolver
  -> trial_facts
  -> rag_retrieval
  -> evidence_packet_builder
  -> domain SQ nodes
  -> judges
  -> verification
  -> overall
  -> reporter
```

After this design:

```text
pdf_ingest
  - parse primary PDF
  - build primary chunks
  - parse optional supplements
  - append supplement chunks with provenance
  - record source_documents and supplement_warnings
  -> unchanged downstream graph
```

ClinicalTrials.gov remains in `preliminary_info`, then becomes packet candidate evidence through `evidence_source_selection.py`.

### Why Ingest Supplements In `pdf_ingest_node`

`rag_retrieval_node` already consumes `docling_chunks`. `evidence_packet_builder` already consumes `rag_chunk_metadata`. By adding supplement chunks before retrieval, the rest of the pipeline can stay mostly unchanged. The main change downstream is that metadata must be preserved and rendered.

---

## Data Model

### New State Fields

Add to `RoB2State`:

```python
supplementary_paths: Annotated[list[str], take_latest]
source_documents: Annotated[list[SourceDocument], take_latest]
supplement_warnings: Annotated[list[str], take_latest]
```

Initialize them in `create_initial_state()`:

```python
"supplementary_paths": list(kwargs.get("supplementary_paths") or []),
"source_documents": [],
"supplement_warnings": [],
```

### New Types

Add to `rob2_pipeline/types.py`:

```python
class SourceDocument(TypedDict, total=False):
    document_id: str
    document_name: str
    document_role: str
    source_kind: str
    path: str
    is_primary: bool
    status: str
    error: str
```

Extend `ChunkMeta`:

```python
class ChunkMeta(TypedDict, total=False):
    text: str
    section: str
    page_numbers: list[int]
    score: float
    document_id: str
    document_name: str
    document_role: str
    source_kind: str
    source_path: str
```

Extend `PacketSource` with the same provenance fields.

### Source Role Vocabulary

Use a small deterministic vocabulary:

- `primary`
- `protocol`
- `sap`
- `appendix`
- `supplementary_methods`
- `supplementary_results`
- `disclosure`
- `data_sharing`
- `registry`
- `unknown_supplement`

`source_kind` remains the broad packet-source mechanism:

- `rag_chunk`
- `section_text`
- `ctgov`
- `targeted_fact` reserved for a later phase

---

## Supplement Triage

Add `rob2_pipeline/ingestion/supplements.py` with focused helpers:

- `classify_supplement(path: Path) -> str`
- `build_source_document(path: Path, role: str, index: int) -> SourceDocument`
- `apply_source_metadata(chunks: list[Document], source: SourceDocument) -> list[Document]`
- `ingest_supplements(paths: list[str]) -> tuple[list[Document], list[SourceDocument], list[str]]`

Classification is deterministic and filename-first:

| Match | Role |
|---|---|
| `sap`, `statistical-analysis`, `statistical_analysis` | `sap` |
| `protocol` | `protocol` |
| `appendix`, `supplement`, `mmc`, `supplementary` | `appendix` |
| `disclosure`, `coi`, `conflict` | `disclosure` |
| `data-sharing`, `data_sharing`, `dss`, `ds_` | `data_sharing` |
| no match | `unknown_supplement` |

Ambiguous files are still indexed as `unknown_supplement`; triage must not suppress parseable supplements.

---

## RAG Changes

### Chunk Metadata

Primary and supplement chunks must carry:

```python
{
    "document_id": "primary" or "supplement:001",
    "document_name": "ARCHES.pdf",
    "document_role": "primary" or "protocol",
    "source_kind": "rag_chunk",
    "source_path": "...",
    "section": "...",
    "page_numbers": [...],
}
```

Update `_doc_key()` to include `document_id` so identical chunks from different PDFs are not deduplicated incorrectly.

### Retrieval Metadata

`retrieve_adaptive()` should copy provenance metadata into returned `ChunkMeta` objects. `rag_chunk_metadata` therefore becomes the audit surface for both primary and supplement retrieval.

### Domain Role Preferences

Add role preference constants in `rag.py` or `evidence_source_selection.py`:

```python
DOMAIN_SOURCE_ROLE_PREFERENCES = {
    "d1": ["primary", "protocol", "appendix"],
    "d2": ["primary", "protocol", "sap", "appendix"],
    "d3": ["primary", "appendix", "sap"],
    "d4": ["primary", "protocol", "sap", "appendix"],
    "d5": ["protocol", "sap", "registry", "primary", "appendix"],
}
```

The first implementation should use these preferences in packet source ranking, not in hard filtering. If retrieval returns only lower-priority roles, they remain eligible.

---

## Evidence Packet Changes

### Candidate Source Pools

`candidate_sources()` should combine:

1. RAG chunk metadata for the contract domain.
2. ClinicalTrials.gov structured packet sources.
3. Existing primary-paper section fallback sources.

The existing section fallback behavior remains unconditional and retains `source_kind="section_text"`.

### ClinicalTrials.gov Packet Sources

Add `ctgov_sources(state, contract)`:

- D1/D2: `ctgov_design`
- D3: `ctgov_flow`
- D5: `ctgov_outcomes`, `registered_endpoint`, `registered_secondary_endpoints`, `registered_analysis`

These sources use:

```python
{
    "source_kind": "ctgov",
    "document_role": "registry",
    "document_name": "ClinicalTrials.gov",
    "page_numbers": [],
}
```

`ctgov` and `section_text` sources are exempt from missing-page warnings. Real `rag_chunk` sources without pages remain a defect.

### Packet Rendering

Packet text should render source provenance:

```text
- Protocol (nejmoa1903307_protocol.pdf), page 14, Statistical Methods: ...
- Main paper (TITAN.pdf), page 6, Results: ...
- ClinicalTrials.gov, registry, Outcomes: ...
```

This replaces ambiguous output such as `page 14, Methods`.

---

## Benchmark and CLI

### Public Assessment API

Extend:

```python
def run_assessment(
    pdf_path: str,
    outcome: str | None = None,
    effect_of_interest: str = DEFAULT_EFFECT_OF_INTEREST,
    output_dir: str = "outputs/",
    supplementary_paths: list[str] | None = None,
) -> RoB2State:
```

### Main CLI

Add:

```text
--supplement PATH     repeatable supplement PDF path
--supplement-dir DIR  directory of supplement PDFs for each assessed PDF
```

For directory input, `--supplement-dir` maps supplements by primary PDF stem:

```text
<supplement-dir>/<primary-stem>/*.pdf
```

### Benchmark API

Extend:

```python
def run_benchmark(
    pdf_dir,
    reference_csvs,
    outcome_map,
    output_dir,
    supplement_dir: str | Path | None = None,
    use_supplements: bool = False,
    supplement_policy: str = "auto",
    **run_kwargs,
) -> list[dict]:
```

Policies:

- `none`: ignore supplements.
- `auto`: use discovered supplements when present; failed supplement parsing records warnings and continues.
- `required`: if `use_supplements=True`, missing supplement folder or supplement parse failure marks the trial as errored.

Default benchmark behavior remains primary-only:

```python
use_supplements=False
```

### Benchmark Layout

Preserve the current layout:

```text
inputs/benchmark/
  ARCHES.pdf
  supplement/
    ARCHES/
      protocol_jco.19.00799.pdf
      ds_jco.19.00799.pdf
```

Add helper:

```python
find_supplements_for_trial(supplement_dir: Path, trial_name: str) -> list[Path]
```

Matching is case-insensitive and preserves names with spaces such as `SWOG 1216`.

### Output JSON

Add these fields to assessment JSON:

- `supplementary_paths`
- `source_documents`
- `supplement_warnings`

`rag_sources` and `evidence_packets[*].sources` should include provenance fields.

Benchmark result entries should include:

- `supplementary_paths`
- `supplements_found`
- `supplement_policy`

---

## Error Handling

- If a supplement path does not exist under `auto`, record a warning and continue.
- If a supplement path does not exist under `required`, raise or mark the trial errored.
- If a supplement parse fails under `auto`, record the failure in `source_documents` and `supplement_warnings`, then continue with remaining sources.
- If all supplement parsing fails but the primary PDF succeeds, the assessment still runs under `auto`.
- Primary PDF parse failure behavior remains unchanged.

---

## Testing Strategy

Add unit tests before implementation for:

- supplement role classification from real benchmark-like filenames
- supplement discovery for `inputs/benchmark/supplement/<TRIAL>/*.pdf`
- trial names with spaces, especially `SWOG 1216`
- source metadata application to chunks
- `_doc_key()` includes `document_id`
- `retrieve_adaptive()` returns provenance metadata
- `rag_retrieval_node()` preserves supplement metadata in `rag_chunk_metadata`
- `candidate_sources()` includes CT.gov sources
- packet rendering includes document name and role
- page warnings are exempt for `ctgov` and `section_text`, but not for `rag_chunk`
- benchmark primary-only behavior is unchanged when `use_supplements=False`
- benchmark passes discovered supplements to `run_assessment()` when `use_supplements=True`

---

## Rollout

1. Implement metadata and API plumbing with primary-only behavior unchanged.
2. Add supplement discovery and parsing behind explicit opt-in.
3. Preserve provenance through RAG and evidence packets.
4. Add CT.gov packet candidate sources.
5. Run focused tests.
6. Run a supplement-enabled benchmark subset and compare accuracy/latency against primary-only baseline.
7. Only after evidence improves, consider enabling supplements by default for benchmark runs.

---

## Deferred Work

The following are deliberately deferred:

- manifest-based per-trial benchmark folders
- LLM-based supplement classification
- remote full-document supplement summarization
- targeted supplement fact extraction as a separate source pool
- ablation reports comparing primary-only versus supplement-enabled judgments

These can be added after the provenance-tagged RAG path has measurable value.
