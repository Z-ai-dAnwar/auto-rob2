# RoB2 Pipeline Architecture

## Overview

The project is organized as a deterministic LangGraph pipeline with LLM-assisted
nodes. The graph processes one PDF at a time and produces:

- `outputs/<pdf>_rob2_report.md`
- `outputs/<pdf>_rob2_data.json`

## Core Modules

- `rob2_pipeline/graph.py`: graph topology and control flow
- `rob2_pipeline/pipeline.py`: public orchestration entrypoint
- `rob2_pipeline/state.py`: shared state contract + reducer annotations
- `rob2_pipeline/state_factory.py`: canonical initial state creation
- `rob2_pipeline/nodes/*`: node implementations
- `rob2_pipeline/judges/*`: deterministic decision logic
- `rob2_pipeline/prompts.py`: prompt templates (API-compatible)
- `rob2_pipeline/prompt_registry.py`: central prompt index
- `rob2_pipeline/llm_client.py`: LLM singleton, retry, and rate limiting
- `rob2_pipeline/cache.py`: optional disk prompt cache
- `rob2_pipeline/xml_parser.py`: robust XML extraction/parsing

## Execution Flow

1. `pdf_ingest`: markdown extraction + regex section bootstrap
2. `rct_screener`: stop early for non-RCT studies
3. `preliminary_info`: trial metadata extraction
4. `section_parser`: LLM section spans with regex fallback
5. Parallel fan-out to domain SQ nodes: D1, D2, D3, D4, D5
6. Domain judge nodes produce deterministic domain judgments
7. `overall_judge`: overall risk + review priority
8. `report_formatter`: markdown + JSON output payload

## Concurrency Model

LangGraph merges parallel node writes via reducers in `RoB2State`:

- `sq_answers`: dict-merge reducer
- `domain_judgments`: dict-merge reducer
- `domain_rationales`: dict-merge reducer
- `llm_call_log`: list concat reducer

Most nodes return **partial updates only** (not full state) to avoid concurrent
channel update collisions.

## Debugging Playbook

### Quick run with summary

```bash
uv run python main.py inputs/example.pdf --debug
```

### Run tests

```bash
uv run python -m pytest -q
```

### Typical failure triage

1. XML parse failures
   - Inspect `state["llm_call_log"]` for `suspected_parse_failures`
   - Check model output for malformed tags/code fences
2. Missing sections
   - Compare `sections` and `__debug_sections`
   - Check `section_parser` output and regex fallback behavior
3. Domain logic disagreements
   - Inspect `sq_answers` and judge modules under `rob2_pipeline/judges/`

## Extending the System

### Add a new domain

1. Add prompt template
2. Add SQ node + judge node
3. Wire graph edges
4. Add state keys/reducers if parallel writers are introduced
5. Add tests for parsing + deterministic judge logic

### Add a new cached LLM node

Use `call_node_llm(...)` from `nodes/common.py` for:

- system prompt enforcement
- optional caching
- parse validation logging

## Production Notes

- Rate limiting is lock-protected for concurrency safety
- LLM client is a process singleton via `lru_cache`
- Cache is opt-in with `ROB2_USE_CACHE=1`
- Cache bypass per-run: `--no-cache`
