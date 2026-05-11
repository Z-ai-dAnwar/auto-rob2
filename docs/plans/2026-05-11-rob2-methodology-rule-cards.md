# RoB 2 Methodology Rule Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace benchmark-shaped prompt guidance with reusable, cited RoB 2 methodology rule cards and add benchmark cohort reporting.

**Architecture:** Add `rob2_pipeline/methodology/` as the canonical source for domain/SQ guidance. Prompt templates render methodology blocks from typed rule cards while preserving existing evidence sections, XML schemas, parsers, and deterministic judges. Benchmark summaries gain optional cohort breakdowns for calibration vs validation evaluation.

**Tech Stack:** Python 3.13+, dataclasses, existing pytest suite, existing benchmark CLI.

---

## Tasks

- [ ] Add methodology dataclasses in `rob2_pipeline/methodology/types.py` with tests.
- [ ] Add methodology renderer in `rob2_pipeline/methodology/render.py` with tests.
- [ ] Add D1-D5 rule-card modules and package exports with structural/citation/no-leakage tests.
- [ ] Integrate rendered methodology blocks into `rob2_pipeline/prompts.py` and replace brittle prompt wording tests.
- [ ] Add benchmark cohort support to `rob2_pipeline/benchmark.py`, `benchmark.py`, and tests.
- [ ] Move D1 RAG query note coverage into `tests/test_rag_queries.py`.
- [ ] Run full tests and benchmark dry-run verification.

## Verification

- `uv run python -m pytest tests/`
- `uv run python benchmark.py --outcome-map CHAARTED:OS:calibration CHAARTED:PFS:calibration PEACE-1:OS:calibration PEACE-1:PFS:calibration PEACE-1:AE:calibration STAMPEDE:OS:calibration STAMPEDE:PFS:calibration STAMPEDE:AE:calibration --dry-run`

## Notes

- Do not change deterministic judge algorithms.
- Do not encode visible benchmark verdicts or trial names in methodology guidance.
- Do not commit implementation changes unless explicitly requested.
