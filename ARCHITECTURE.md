# Architecture

## Pipeline Overview

`auto-rob2` runs a sequential LangGraph workflow:

1. PDF ingestion and section parsing
2. RCT screening
3. Preliminary trial metadata extraction
4. Domain-level signaling questions (D1-D5)
5. Deterministic domain judgments
6. Deterministic overall judgment
7. Report generation (Markdown + JSON)

Main graph wiring is in `rob2_pipeline/graph.py`.

## Core Components

- `rob2_pipeline/pdf_ingestion.py`
  - Extracts full text and section-level snippets.
  - Includes CONSORT augmentation fallback from results/supplementary text.

- `rob2_pipeline/prompts.py`
  - Prompt templates for RCT screening, preliminary extraction, and D1-D5 signaling questions.

- `rob2_pipeline/nodes/`
  - LangGraph node implementations.
  - `nodes/common.py` centralizes provider-backed LLM calls, cache reads/writes, and parse-repair.
  - `nodes/preliminary.py` also enriches registration data via ClinicalTrials.gov API v2.

- `rob2_pipeline/providers/`
  - Provider abstraction around LangChain chat models.
  - Supported providers: `openrouter`, `anthropic`, `openai`.
  - Selection is configured by `ROB2_PROVIDER` and built via `rob2_pipeline.config.build_provider()`.

- `rob2_pipeline/registration_api.py`
  - Fetches and formats outcomes from ClinicalTrials.gov API v2.
  - Used to populate `ctgov_outcomes` and improve Domain 5 context.

- `rob2_pipeline/judges/`
  - Deterministic RoB 2 decision tables for D1-D5 and overall judgment.
  - These functions implement the adjudication logic; LLMs do not set final judgments directly.

## State Model

State schema is defined in `rob2_pipeline/state.py` and initialized in `rob2_pipeline/state_factory.py`.

Important fields:

- `sq_answers`: parsed signaling-question answers
- `domain_judgments`, `domain_rationales`
- `effect_of_interest`: `ITT` or `per-protocol`
- `registered_endpoint`, `registered_secondary_endpoints`
- `ctgov_outcomes`
- `llm_call_log`, `errors`

## Runtime and Configuration

- Provider selection: `ROB2_PROVIDER` (`openrouter`, `anthropic`, `openai`)
- Provider keys:
  - `OPENROUTER_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `OPENAI_API_KEY`
- LLM config:
  - `ROB2_MODEL`, `ROB2_TEMPERATURE`, `ROB2_MAX_TOKENS`
  - `ROB2_RPM_LIMIT`, `ROB2_RPD_LIMIT`
- Effect of interest: `ROB2_EFFECT_OF_INTEREST` (`ITT` or `per-protocol`)
- Caches:
  - Prompt cache: `ROB2_USE_CACHE` (`.rob2_cache/`)
  - ClinicalTrials.gov cache: `ROB2_CTGOV_CACHE`

All LLM invocations should use LangChain/LangGraph integrations (no direct provider HTTP API calls in pipeline LLM execution paths).
