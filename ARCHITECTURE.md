# Architecture

## Pipeline Overview

`auto-rob2` runs a LangGraph workflow with Docling-based ingestion, local retrieval, and deterministic RoB 2 adjudication:

1. PDF ingestion, OCR retry, section/table parsing, and Docling chunking
2. RCT screening
3. Preliminary trial metadata extraction with ClinicalTrials.gov enrichment
4. Per-document RAG retrieval from Docling chunks, with section fallback
5. Parallel domain-level signaling-question fan-out (D1-D5)
6. Deterministic domain judgments
7. Deterministic overall judgment
8. Report generation (Markdown + JSON)

Main graph wiring is in `rob2_pipeline/graph.py`.

Outputs per run:

- `outputs/<pdf>_rob2_report.md`
- `outputs/<pdf>_rob2_data.json`

## Core Components

- `rob2_pipeline/pdf_ingestion.py`
  - Extracts full text with LangChain Docling markdown export.
  - Retries Docling conversion with OCR enabled when non-OCR extraction fails.
  - Builds a structured document representation preserving section headings and markdown tables.
  - Creates domain evidence from Docling structure, optionally refines evidence with an ingestion-time LLM XML extraction, and falls back to deterministic keyword mapping on failure.
  - Builds LangChain `Document` chunks using Docling `HybridChunker` with a Hugging Face tokenizer configured for `sentence-transformers/all-MiniLM-L6-v2`, 256-token chunks, and long counting windows.
  - Includes CONSORT augmentation fallback from results/supplementary text and D3 censoring-context extraction.

- `rob2_pipeline/docling_utils.py`
  - Small Docling compatibility helpers for item label names and markdown table export across Docling versions.

- `rob2_pipeline/rag.py`
  - Embeds Docling chunks with `sentence-transformers/all-MiniLM-L6-v2` via `langchain-huggingface`.
  - Builds FAISS indexes from the current document only.
  - Builds optional section-filtered indexes per domain and falls back to the full index if filtered recall is too sparse.
  - Performs adaptive multi-query retrieval within a token budget and returns both context text and chunk metadata.

- `rob2_pipeline/rag_queries.py`
  - Static query sets for D1-D5 retrieval contexts.
  - D1 queries are trial-level and intentionally outcome-agnostic.

- `rob2_pipeline/methodology/`
  - Canonical RoB 2 methodology guidance used by prompts.
  - `types.py` defines citations, response rules, rule cards, and domain methodology containers.
  - `domain1.py` through `domain5.py` define source-backed SQ guidance.
  - `render.py` turns selected rule cards into compact prompt sections.

- `rob2_pipeline/pipeline.py`
  - Public orchestration entrypoint for assessments.

- `rob2_pipeline/prompts.py`
  - Prompt templates for RCT screening, preliminary extraction, and D1-D5 signaling questions.
  - Imports rendered methodology blocks from `rob2_pipeline/methodology/` so SQ guidance has one canonical source.

- `rob2_pipeline/nodes/`
  - LangGraph node implementations.
  - `nodes/common.py` centralizes provider-backed LLM calls, cache reads/writes, and parse-repair.
  - `nodes/ingest.py` coordinates Docling extraction, optional remote evidence extraction, fallback evidence extraction, and RCT screening.
  - `nodes/preliminary.py` also enriches registration data via ClinicalTrials.gov API v2.
  - `nodes/rag_retrieval.py` builds `rag_contexts` and `rag_chunk_metadata` from Docling chunks, or falls back to structured evidence sections.

- `rob2_pipeline/providers/`
  - Provider abstraction around LangChain chat models.
  - Supported providers: `openrouter`, `anthropic`, `openai`.
  - Selection is configured by `ROB2_PROVIDER` and built via `rob2_pipeline.config.build_provider()`.

- `rob2_pipeline/registration_api.py`
  - Fetches and formats outcomes from ClinicalTrials.gov API v2.
  - Used to populate `ctgov_outcomes`, `ctgov_design`, `ctgov_description`, `ctgov_flow`, and registered endpoint fields.

- `rob2_pipeline/judges/`
  - Deterministic RoB 2 decision tables for D1-D5 and overall judgment.
  - These functions implement the adjudication logic; LLMs do not set final judgments directly.

- `rob2_pipeline/cache.py`
  - Optional disk prompt cache utilities.

- `rob2_pipeline/xml_parser.py`
  - Strict XML extraction/parsing for SQ answers and metadata.

- `rob2_pipeline/benchmark.py`
  - Loads reference CSV rows, runs assessments for requested trial/outcome pairs, compares judgments, builds confusion matrices, and writes benchmark Markdown/JSON reports.
  - Supports optional cohort labels such as `calibration` and `validation`; default `unspecified` labels are stored in JSON but hidden from Markdown reports when no meaningful labels are present.

## Execution Flow

1. `pdf_ingest`: markdown extraction + deterministic section parsing
   - `extract_full_text` uses LangChain Docling markdown export, first without OCR and then with OCR if needed.
   - A non-OCR Docling conversion is reused to build chunks and a structured document representation.
   - Structural evidence is always available when Docling succeeds.
   - Optional LLM evidence refinement runs only when remote extraction is enabled and the document appears to be an RCT candidate.
   - If Docling structure fails, keyword-based evidence fallback is used.
2. `rct_screener`: stop early for non-RCT studies
3. `preliminary_info`: trial metadata extraction
4. `rag_retrieval`: per-document embedding, section-filtered retrieval, metadata capture, and D3 censoring-context augmentation
5. Parallel fan-out to domain SQ nodes: D1, D2, D3, D4, D5
6. D2 branches internally from SQ 2.1/2.2 to conditional questions when needed, then analysis questions
7. Domain judge nodes produce deterministic domain judgments
8. `overall_judge`: overall risk + review priority
9. `report_formatter`: markdown report payload

## Concurrency Model

LangGraph merges parallel node writes via reducers in `RoB2State`:

- `sq_answers`: dict-merge reducer
- `domain_judgments`: dict-merge reducer
- `domain_rationales`: dict-merge reducer
- `rag_chunk_metadata`: dict-merge reducer
- `llm_call_log`: list concat reducer

Most nodes return partial updates only (not full state) to avoid concurrent channel update collisions.

## State Model

State schema is defined in `rob2_pipeline/state.py` and initialized in `rob2_pipeline/state_factory.py`.

Important fields:

- `sq_answers`: parsed signaling-question answers
- `domain_judgments`, `domain_rationales`
- `docling_doc`, `rag_contexts`
- `docling_chunks`, `rag_chunk_metadata`
- `effect_of_interest`: `ITT` or `per-protocol`
- `registered_endpoint`, `registered_secondary_endpoints`
- `ctgov_outcomes`, `ctgov_design`, `ctgov_description`, `ctgov_flow`
- `llm_call_log`, `errors`

## Runtime and Configuration

- Provider selection: `ROB2_PROVIDER` (`openrouter`, `anthropic`, `openai`)
- Provider keys:
  - `OPENROUTER_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `OPENAI_API_KEY`
- Hugging Face auth may be needed once for the embedding model download:
  - `hf auth login`
  - or set `HF_TOKEN`
- LLM config:
  - `ROB2_MODEL`, `ROB2_TEMPERATURE`, `ROB2_MAX_TOKENS`
  - `ROB2_RPM_LIMIT`, `ROB2_RPD_LIMIT`
- Effect of interest: `ROB2_EFFECT_OF_INTEREST` (`ITT` or `per-protocol`)
- Ingestion evidence refinement: `ROB2_REMOTE_EVIDENCE_EXTRACTION`
  - default enabled
  - set to `0`, `false`, or `False` to skip the ingestion-time LLM evidence extraction and use Docling structural evidence only
- Caches:
  - Prompt cache: `ROB2_USE_CACHE` (`.rob2_cache/`)
  - ClinicalTrials.gov cache: `ROB2_CTGOV_CACHE`

All LLM invocations should use LangChain/LangGraph integrations (no direct provider HTTP API calls in pipeline LLM execution paths).

## Debugging Playbook

Quick run with summary:

```bash
uv run python main.py inputs/example.pdf --debug
```

Run tests:

```bash
uv run python -m pytest -q
```

Run focused tests:

```bash
uv run python -m pytest tests/test_benchmark.py -q
```

Syntax-check changed Python files when a full test run is unnecessary:

```bash
uv run python -m py_compile rob2_pipeline/benchmark.py tests/test_benchmark.py
```

Validate benchmark inputs without LLM calls:

```bash
uv run python benchmark.py \
  --outcome-map CHAARTED:OS:calibration CHAARTED:PFS:validation \
  --dry-run
```

Typical failure triage:

1. XML parse failures
   - `call_node_llm` retries once with a repair prompt, then raises if output is still invalid
   - Check model output for malformed tags/code fences
2. Missing sections
   - Check deterministic section headings and patterns in `rob2_pipeline/pdf_ingestion.py`
   - Check evidence extraction warnings in the JSON output; Docling structural failures are reported there
3. RAG retrieval gaps
   - Inspect `rag_contexts` and `rob2_pipeline/rag.py`
   - Inspect JSON `rag_sources` for chunk text, section labels, page numbers, and similarity scores
4. Domain logic disagreements
   - Inspect `sq_answers` and judge modules under `rob2_pipeline/judges/`

## Extending the System

Add a new domain:

1. Add methodology rule cards under `rob2_pipeline/methodology/`
2. Add prompt template that renders the relevant methodology block
3. Add SQ node + judge node
4. Wire graph edges
5. Add state keys/reducers if parallel writers are introduced
6. Add tests for methodology rendering, parsing, and deterministic judge logic

Add a new cached LLM node:

Use `call_node_llm(...)` from `nodes/common.py` for:

- system prompt enforcement
- optional caching
- parse validation logging

## Production Notes

- Rate limiting is lock-protected for concurrency safety
- Cache is opt-in with `ROB2_USE_CACHE=1`
- Cache bypass per-run: `--no-cache`
