# Architecture

## Pipeline Overview

`auto-rob2` runs a LangGraph workflow with local retrieval and deterministic RoB 2 adjudication:

1. PDF ingestion and section parsing
2. RCT screening
3. Preliminary trial metadata extraction with ClinicalTrials.gov enrichment
4. Per-document RAG retrieval from Docling chunks
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
  - Extracts full text and section-level snippets.
  - Includes CONSORT augmentation fallback from results/supplementary text.

- `rob2_pipeline/rag.py`
  - Builds local Docling chunks, embeds them with `sentence-transformers/all-MiniLM-L6-v2`, and retrieves with FAISS.

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
  - `nodes/preliminary.py` also enriches registration data via ClinicalTrials.gov API v2.
  - `nodes/rag_retrieval.py` builds `rag_contexts` from the per-document Docling result.

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
2. `rct_screener`: stop early for non-RCT studies
3. `preliminary_info`: trial metadata extraction
4. `rag_retrieval`: per-document chunking, embedding, and local retrieval
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
- `llm_call_log`: list concat reducer

Most nodes return partial updates only (not full state) to avoid concurrent channel update collisions.

## State Model

State schema is defined in `rob2_pipeline/state.py` and initialized in `rob2_pipeline/state_factory.py`.

Important fields:

- `sq_answers`: parsed signaling-question answers
- `domain_judgments`, `domain_rationales`
- `docling_doc`, `rag_contexts`
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
3. RAG retrieval gaps
   - Inspect `rag_contexts` and `rob2_pipeline/rag.py`
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
