# Pipeline Timing Instrumentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add instrumentation-only timing data to pipeline traces and benchmark artifacts.

**Architecture:** Extend the active trace with graph-node spans, wrap graph nodes centrally, and summarize trace timing in benchmark results and reports. Keep behavior additive: no prompt, provider, graph topology, cache, or accuracy changes.

**Tech Stack:** Python 3.13, LangGraph, pytest, JSON benchmark artifacts.

---

### Task 1: Trace Node Spans

**Files:**
- Modify: `rob2_pipeline/trace.py`
- Test: `tests/test_trace.py`

- [ ] **Step 1: Write failing trace span tests**

Add tests that start a trace, record one successful span through a context manager, record one failed span, and assert serialization includes `node_spans`.

- [ ] **Step 2: Run trace tests and verify failure**

Run: `uv run python -m pytest tests/test_trace.py -q`

Expected: FAIL because `record_node_span` or equivalent span support does not exist.

- [ ] **Step 3: Implement minimal span model and helper**

Add a `PipelineNodeSpan` dataclass, `node_spans` to `PipelineTrace`, and a context manager that records status, duration, timestamps, and errors while re-raising exceptions.

- [ ] **Step 4: Run trace tests and verify pass**

Run: `uv run python -m pytest tests/test_trace.py -q`

Expected: PASS.

### Task 2: Central Graph Node Wrapping

**Files:**
- Modify: `rob2_pipeline/graph.py`
- Test: `tests/test_graph.py`

- [ ] **Step 1: Write failing wrapper tests**

Add direct tests for a small exported wrapper helper. One fake node should return normally and create an `ok` span; another should raise and create an `error` span.

- [ ] **Step 2: Run graph wrapper tests and verify failure**

Run: `uv run python -m pytest tests/test_graph.py -q`

Expected: FAIL because the wrapper helper is not implemented.

- [ ] **Step 3: Implement central wrapper and apply it to all graph nodes**

Add a helper such as `_timed_node(name, fn)` and use it for every `g.add_node()` call. The helper must not change node inputs or outputs.

- [ ] **Step 4: Run graph tests and verify pass**

Run: `uv run python -m pytest tests/test_graph.py -q`

Expected: PASS.

### Task 3: Benchmark Timing Summaries

**Files:**
- Modify: `rob2_pipeline/benchmark.py`
- Test: `tests/test_benchmark.py`

- [ ] **Step 1: Write failing benchmark timing tests**

Add tests for extracting timing from a fake trace file, fallback behavior when the trace file is missing, and `run_benchmark()` attaching `timing` to a result even when `run_assessment()` is monkeypatched.

- [ ] **Step 2: Run benchmark tests and verify failure**

Run: `uv run python -m pytest tests/test_benchmark.py -q`

Expected: FAIL because benchmark timing helpers and result fields do not exist.

- [ ] **Step 3: Implement timing extraction and per-result timing**

Use `time.perf_counter()` around `run_assessment()`, load `{pdf_stem}_trace.json` from the assessment output directory, summarize `llm_calls` and `node_spans`, and attach the timing object to each result.

- [ ] **Step 4: Run benchmark tests and verify pass**

Run: `uv run python -m pytest tests/test_benchmark.py -q`

Expected: PASS.

### Task 4: Benchmark Summary and Markdown Report

**Files:**
- Modify: `rob2_pipeline/benchmark.py`
- Test: `tests/test_benchmark.py`

- [ ] **Step 1: Write failing report tests**

Add tests that `summarize_benchmark()` includes aggregate timing metrics and `write_benchmark_report()` renders a `## Timing Summary` section with run and node timing tables.

- [ ] **Step 2: Run benchmark tests and verify failure**

Run: `uv run python -m pytest tests/test_benchmark.py -q`

Expected: FAIL because timing summary/report rendering is missing.

- [ ] **Step 3: Implement aggregate timing summary and report rendering**

Compute evaluated-run timing totals, mean/median wall time, LLM totals, cache hits, slowest runs, and node aggregates. Render seconds with one decimal place in Markdown.

- [ ] **Step 4: Run benchmark tests and verify pass**

Run: `uv run python -m pytest tests/test_benchmark.py -q`

Expected: PASS.

### Task 5: Final Verification

**Files:**
- Verify all modified code and docs.

- [ ] **Step 1: Run focused tests**

Run: `uv run python -m pytest tests/test_trace.py tests/test_graph.py tests/test_benchmark.py -q`

Expected: PASS.

- [ ] **Step 2: Run full test suite**

Run: `uv run python -m pytest -q`

Expected: PASS.

- [ ] **Step 3: Run benchmark dry run**

Run: `uv run python benchmark.py --outcome-map CHAARTED:OS --dry-run`

Expected: dry-run validation output with no LLM calls.

- [ ] **Step 4: Review diff**

Run: `git diff --stat` and `git diff --check`

Expected: only timing instrumentation, tests, and the plan changed; no whitespace errors.
