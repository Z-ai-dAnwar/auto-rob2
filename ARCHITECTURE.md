# Architecture

## Pipeline Overview

`auto-rob2` runs a LangGraph workflow for automated first-pass Cochrane Risk of Bias 2 assessment. LLMs extract structured trial facts and signaling-question answers, while deterministic Python judges compute domain and overall RoB 2 judgments.

The compiled graph in `rob2_pipeline/graph.py` executes these stages:

1. PDF ingestion, OCR retry, section/table parsing, and Docling chunking
2. RCT screening
3. Preliminary trial metadata extraction with ClinicalTrials.gov enrichment
4. Outcome-property normalization and trial-fact extraction
5. Per-document RAG retrieval from Docling chunks, with fallback contexts and retrieval grading
6. SQ-specific evidence packet construction
7. Parallel domain-level signaling-question fan-out (D1-D5)
8. Deterministic domain judgments
9. Quote and packet verification
10. Deterministic overall judgment and human-review priority
11. Report generation (Markdown report payload, then JSON/Markdown writes in `pipeline.py`)

Outputs per run:

- `outputs/<pdf>_rob2_report.md`
- `outputs/<pdf>_rob2_data.json`

If `rct_screener` determines a paper is not an RCT, the graph terminates early. JSON output is still written; Markdown may be absent because the report formatter does not run.

## Core Components

- `rob2_pipeline/pdf_ingestion.py`
  - Compatibility facade for ingestion helpers used by graph nodes and tests.
  - Re-exports focused modules under `rob2_pipeline/ingestion/`.

- `rob2_pipeline/ingestion/`
  - `docling_extract.py`: Docling text extraction, OCR retry, converter caching, and chunk creation.
  - `document_repr.py`: Docling item traversal and prompt-facing document representation.
  - `evidence.py`: paper evidence extraction, structural section mapping, keyword fallbacks, and censoring context.
  - `settings.py`: ingestion constants and runtime feature flags.

- `rob2_pipeline/docling_utils.py`
  - Small Docling compatibility helpers for item label names and markdown table export across Docling versions.

- `rob2_pipeline/rag.py`
  - Embeds Docling chunks with `BAAI/bge-small-en-v1.5` via `langchain-huggingface`.
  - Builds FAISS indexes from the current document only.
  - Builds optional section-filtered indexes per domain and falls back to the full index if filtered recall is too sparse.
  - Performs adaptive multi-query retrieval within a token budget and returns both context text and chunk metadata.
  - Grades retrieved context by domain for relevance, coverage, missing evidence, and retry recommendation.

- `rob2_pipeline/rag_queries.py`
  - Static query sets for each signaling question.
  - `domain_queries()` aggregates SQ queries into D1-D5 retrieval contexts.

- `rob2_pipeline/methodology/`
  - Canonical RoB 2 methodology guidance used by prompts.
  - `types.py` defines citations, response rules, rule cards, and domain methodology containers.
  - `domain1.py` through `domain5.py` define source-backed SQ guidance.
  - `render.py` turns selected rule cards into compact prompt sections.

- `rob2_pipeline/prompts.py`
  - Prompt templates for RCT screening, preliminary extraction, and D1-D5 signaling questions.
  - Imports rendered methodology blocks from `rob2_pipeline/methodology/` so SQ guidance has one canonical source.

- `rob2_pipeline/nodes/`
  - LangGraph node implementations.
  - `nodes/common.py` centralizes provider-backed LLM calls, cache reads/writes, and parse-repair.
  - `nodes/domain_helpers.py` shares simple domain SQ call helpers across domain nodes.
  - `nodes/ingest.py` coordinates Docling extraction, optional remote evidence extraction, fallback evidence extraction, and RCT screening.
  - `nodes/preliminary.py` also enriches registration data via ClinicalTrials.gov API v2.
  - `nodes/outcome_resolver.py` normalizes outcome type from inferred properties such as time-to-event, safety, objective event, and blinded adjudication.
  - `nodes/trial_facts.py` extracts reusable deterministic snippets for randomization, concealment, masking, deviations, amendments, and analysis populations.
  - `nodes/rag_retrieval.py` builds domain-level retrieval contexts, prompt-facing D2/D4 context variants, chunk metadata, and retrieval grades; if vector retrieval fails, it falls back to structured evidence sections.
  - `nodes/evidence_packets.py` orchestrates SQ-level packet construction and prompt-facing packet rendering.
  - Contract definitions, source selection, and packet grading live in focused sibling modules.
  - `nodes/verification.py` verifies SQ quotes and packet quality, then emits validation flags and recommended retry/escalation actions.
  - `nodes/reporter.py` writes the Markdown report, including verified-packet and quality-flag summaries.

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

- `rob2_pipeline/types.py`
  - Shared typed structures for LLM call logs, retrieval metadata, outcome properties, trial facts, evidence packets/facts, retrieval grades, and verifier traces.

- `rob2_pipeline/xml_parser.py`
  - Strict XML extraction/parsing for SQ answers and metadata.

- `rob2_pipeline/benchmark.py`
  - Loads reference CSV rows, runs assessments for requested trial/outcome pairs, compares judgments, builds confusion matrices, and writes benchmark Markdown/JSON reports.
  - Supports optional cohort labels such as `calibration` and `validation`; default `unspecified` labels are stored in JSON but hidden from Markdown reports when no meaningful labels are present.

- `rob2_pipeline/pipeline.py`
  - Public orchestration entrypoint for assessments.
  - Writes the Markdown report when available and always writes JSON diagnostics for the completed state.

## Execution Flow

1. `pdf_ingest`: markdown extraction + deterministic section parsing
   - `extract_full_text` uses LangChain Docling markdown export, first without OCR and then with OCR if needed.
   - The ingest node then performs a non-OCR Docling conversion used for chunks and structural document representation.
   - Structural evidence is available when that conversion succeeds.
   - Optional LLM evidence refinement runs only when remote extraction is enabled and the document appears to be an RCT candidate.
   - If Docling structure fails, keyword-based evidence fallback is used.
2. `rct_screener`: stop early for non-RCT studies
3. `preliminary_info`: trial metadata extraction
   - Uses paper evidence, then fetches ClinicalTrials.gov API v2 data when an NCT number is available.
   - Can auto-select a registered secondary endpoint that matches the assessed outcome.
   - Auto-sets the effect of interest to `per-protocol` for detected safety endpoints when `ROB2_EFFECT_OF_INTEREST` is at its `ITT` default.
4. `outcome_resolver`: normalizes `outcome_type` from `outcome_properties`
5. `trial_facts`: extracts reusable trial-level snippets for prompt grounding
6. `rag_retrieval`: per-document embedding, section-filtered retrieval, metadata capture, retrieval grading, compatibility context mapping for D2/D4 prompt groups, and D3 censoring-context augmentation
7. `evidence_packet_builder`: builds SQ-specific packets with required-evidence contracts, candidate facts, negative flags, and packet grades
8. Parallel fan-out to domain SQ nodes: D1, D2, D3, D4, D5
9. D2 branches internally from SQ 2.1/2.2 to conditional questions when needed, then analysis questions
10. Domain judge nodes produce deterministic domain judgments
11. `quote_verifier`: checks quote support and packet quality, and records validation flags/actions
12. `overall_judge`: overall risk + review priority
13. `report_formatter`: markdown report payload

## Concurrency Model

LangGraph merges parallel node writes via reducers in `RoB2State`:

- `sq_answers`: dict-merge reducer
- `domain_judgments`: dict-merge reducer
- `domain_rationales`: dict-merge reducer
- `rag_chunk_metadata`: dict-merge reducer
- `retrieval_grades`: dict-merge reducer
- `evidence_packets`: dict-merge reducer
- `evidence_facts`: dict-merge reducer
- `packet_grades`: dict-merge reducer
- `llm_call_log`: list concat reducer

Most nodes return partial updates only (not full state) to avoid concurrent channel update collisions. Sequential nodes use latest-value reducers for scalar and list outputs such as `verification_actions`.

## State Model

State schema is defined in `rob2_pipeline/state.py` and initialized in `rob2_pipeline/state_factory.py`.

Important fields:

- `pdf_path`, `full_text`, `evidence`: source input and extracted paper evidence.
- `docling_doc`, `docling_chunks`: non-JSON Docling conversion result and LangChain `Document` chunks.
- `rag_contexts`: prompt-facing context strings. Current keys are `d1`, `d2_blinding`, `d2_deviations`, `d2_analysis`, `d3`, `d4_measurement`, `d4_assessor`, and `d5`.
- `rag_chunk_metadata`: JSON-emitted as `rag_sources`, grouped by domain (`d1` through `d5`) with text, section, pages, and score.
- `retrieval_grades`, `evidence_packets`, `evidence_facts`, `packet_grades`: retrieval and evidence-packet diagnostics.
- `sq_answers`: parsed signaling-question answers
- `domain_judgments`, `domain_rationales`
- `effect_of_interest`: `ITT` or `per-protocol`
- `outcome_properties`
- `registered_endpoint`, `registered_secondary_endpoints`
- `ctgov_outcomes`, `ctgov_design`, `ctgov_description`, `ctgov_flow`
- `sources_consulted`, `trial_facts`
- `evidence_validation_flags`, `verifier_trace`, `verification_actions`
- `overall_policy`
- `llm_call_log`, `errors`

## Runtime and Configuration

- Provider selection: `ROB2_PROVIDER` (`openrouter`, `anthropic`, `openai`)
- Provider keys:
  - `OPENROUTER_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `OPENAI_API_KEY`
- Hugging Face auth may be needed once for the `BAAI/bge-small-en-v1.5` tokenizer/embedding download:
  - `hf auth login`
  - or set `HF_TOKEN`
- LLM config:
  - `ROB2_MODEL`, `ROB2_TEMPERATURE`, `ROB2_MAX_TOKENS`
  - `ROB2_RPM_LIMIT`, `ROB2_RPD_LIMIT`
- Effect of interest: `ROB2_EFFECT_OF_INTEREST` (`ITT` or `per-protocol`)
  - The preliminary node may auto-switch safety endpoints to `per-protocol` when this environment setting is at its `ITT` default.
- Ingestion evidence refinement: `ROB2_REMOTE_EVIDENCE_EXTRACTION`
  - default enabled
  - set to `0`, `false`, or `False` to skip the ingestion-time LLM evidence extraction and use Docling structural evidence only
- Caches:
  - Prompt cache: `ROB2_USE_CACHE` (`.rob2_cache/`)
  - ClinicalTrials.gov cache: `ROB2_CTGOV_CACHE`

Provider credentials can live in `.env` because `build_provider()` calls `load_dotenv()`. Settings read at module import time, such as `ROB2_PROVIDER`, `ROB2_MODEL`, and rate limits, should be exported in the process environment before invoking the CLI when they differ from defaults.

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
   - Inspect `retrieval_grades` for missing domain terms and retry recommendations
   - If `rag_sources` is empty, check `evidence.warnings` for vector retrieval failure and confirm the BGE embedding model is available locally or downloadable from Hugging Face.
4. Evidence packet or quote verification flags
   - Inspect `evidence_packets`, `packet_grades`, and `evidence_validation_flags`
   - `verification_actions` indicates whether to retry an SQ with a verified packet or escalate packet retrieval
5. Domain logic disagreements
   - Inspect `sq_answers` and judge modules under `rob2_pipeline/judges/`

## Extending the System

Add a new domain:

1. Add methodology rule cards under `rob2_pipeline/methodology/`
2. Add prompt template that renders the relevant methodology block
3. Add SQ retrieval queries and evidence-packet contracts
4. Add SQ node + judge node
5. Wire graph edges, including quote verification before overall judgment
6. Add state keys/reducers if parallel writers are introduced
7. Add tests for retrieval grading, packet construction, methodology rendering, parsing, and deterministic judge logic

Add a new cached LLM node:

Use `call_node_llm(...)` from `nodes/common.py` for:

- system prompt enforcement
- optional caching
- parse validation logging

## Production Notes

- Rate limiting is lock-protected for concurrency safety
- Cache is opt-in with `ROB2_USE_CACHE=1`
- Cache bypass per-run: `--no-cache`
