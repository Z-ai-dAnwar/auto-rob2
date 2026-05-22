# Pipeline Timing Instrumentation Design

## Context

The RoB 2 benchmark pipeline currently produces accuracy-oriented artifacts, including `benchmark_results.json`, `benchmark_report.md`, per-assessment data JSON, and detailed LLM I/O traces. Runtime is now a major evaluation concern: a single study/outcome can take about 10-13 minutes, and some of that delay may come from slow queue-based OpenRouter free-tier calls to GPT-OSS 120B.

The existing trace already records LLM call latency, tokens, cache hits, parse failures, and repairs. That is useful but incomplete. It does not show total wall-clock time for graph nodes such as PDF ingestion, Docling conversion, supplement ingestion, RAG indexing/retrieval, deterministic judgment logic, quote verification orchestration, or report formatting. Benchmark output also does not summarize timing, so performance comparisons require manual inspection.

## Goal

Add instrumentation-only timing observability that lets benchmark runs identify which pipeline components consume the most time without changing assessment behavior, prompts, model selection, caching policy, graph topology, RAG behavior, supplement behavior, or benchmark accuracy logic.

## Non-Goals

- Do not optimize runtime in this change.
- Do not change model defaults, provider defaults, rate limits, prompt text, parsing behavior, or retry behavior.
- Do not add parallel benchmark execution yet.
- Do not remove or replace the existing LLM trace format.
- Do not require live LLM calls for unit tests.

## Recommended Approach

Implement first-class pipeline profiling in the trace system and surface summarized timing in benchmark artifacts.

The trace should become the source of truth for detailed timing. Benchmark reporting should consume the trace and present concise timing summaries. This keeps the design useful as the graph evolves: new nodes can be timed through graph wrapping, and benchmark output remains a stable view over the richer trace data.

## Architecture

### Trace Layer

Extend `rob2_pipeline/trace.py` with a span model for graph-node execution. Each span should record:

- `node`: graph node name.
- `timestamp_start`: UTC ISO timestamp.
- `timestamp_end`: UTC ISO timestamp or `None` if not closed.
- `duration_ms`: elapsed wall-clock duration measured with `time.perf_counter()`.
- `status`: `ok` or `error`.
- `error`: short error string when the node raises.

The existing `LlmNodeTrace` records should remain unchanged except for any additive fields required by tests. LLM calls and node spans represent different timing layers:

- LLM call latency shows provider-facing time for individual calls.
- Node spans show wall-clock time for each graph node, including non-LLM work and any nested LLM calls.

### Graph Layer

Instrument nodes centrally in `rob2_pipeline/graph.py` instead of scattering timers through every node implementation.

Add a small wrapper helper around every node callable before registering it with LangGraph. The wrapper should:

1. Start a span using the active trace.
2. Call the original node.
3. Close the span with `status="ok"` when the node returns.
4. Close the span with `status="error"` and the exception message when the node raises, then re-raise the original exception.

This central wrapping keeps future graph changes easy to profile. If a new node is added to the graph, the developer should register it through the same wrapper path.

### Pipeline Layer

Keep `run_assessment()` responsible for starting and ending traces. Add no behavioral changes to the graph invocation or output JSON generation.

The trace written by `trace.write(output_dir)` should include both:

- `llm_calls`: existing detailed LLM I/O records.
- `node_spans`: new detailed graph-node timing records.

### Benchmark Layer

Update `rob2_pipeline/benchmark.py` to record total wall-clock time around `run_assessment()` for each trial/outcome and then read the trace JSON written in that assessment output directory.

Each benchmark result should get a `timing` object:

```json
{
  "total_wall_ms": 725000,
  "trace_available": true,
  "node_total_ms": 721500,
  "llm_total_ms": 610000,
  "non_llm_estimated_ms": 115000,
  "llm_calls": 12,
  "llm_cache_hits": 0,
  "llm_repairs": 1,
  "llm_parse_errors": 1,
  "slowest_nodes": [
    {"node": "domain3_sq", "duration_ms": 110000, "status": "ok"},
    {"node": "pdf_ingest", "duration_ms": 95000, "status": "ok"}
  ],
  "llm_by_node": {
    "domain3_sq": {
      "calls": 1,
      "latency_ms": 110000,
      "input_tokens": 5200,
      "output_tokens": 900,
      "cache_hits": 0,
      "repairs": 0,
      "parse_errors": 0
    }
  }
}
```

`non_llm_estimated_ms` should be `max(total_wall_ms - llm_total_ms, 0)`. This is an estimate because node spans and LLM calls may overlap if LangGraph executes branches concurrently. The report should label it as estimated.

If trace loading fails, the result should still include:

```json
{
  "total_wall_ms": 725000,
  "trace_available": false,
  "trace_error": "trace file not found",
  "node_total_ms": 0,
  "llm_total_ms": 0,
  "non_llm_estimated_ms": 725000,
  "llm_calls": 0,
  "llm_cache_hits": 0,
  "llm_repairs": 0,
  "llm_parse_errors": 0,
  "slowest_nodes": [],
  "llm_by_node": {}
}
```

### Benchmark Report

Add a timing section to `benchmark_report.md` after the agreement summary and before per-trial details.

The report should include:

- Total evaluated wall-clock time.
- Median and mean wall-clock time per evaluated run.
- Total LLM latency.
- Total LLM calls.
- Total cache hits.
- A slowest-run table with trial/outcome, total wall time, LLM time, estimated non-LLM time, LLM call count, cache hits, and slowest node.
- A node aggregate table across evaluated runs with node call count, total duration, mean duration, max duration, and error count.

Markdown output should stay compact and readable. Timing values should be shown in seconds with one decimal place for report readability while JSON keeps integer milliseconds.

## Data Flow

1. `run_benchmark()` resolves a trial/outcome and creates `assessment_output_dir`.
2. `run_benchmark()` starts a wall-clock timer.
3. `run_benchmark()` calls `run_assessment()`.
4. `run_assessment()` starts the active trace and invokes the graph.
5. Graph node wrappers append node spans to the active trace.
6. Existing LLM helpers append LLM call traces to the active trace.
7. `run_assessment()` ends and writes the trace JSON.
8. `run_benchmark()` stops its wall-clock timer.
9. `run_benchmark()` loads the trace JSON and stores a summarized `timing` object on the result.
10. `summarize_benchmark()` adds timing aggregates to the summary.
11. `write_benchmark_report()` renders timing summary tables.

## Error Handling

Node span wrappers must close spans on exceptions and re-raise the original error.

Benchmark timing must be best-effort. If `run_assessment()` raises, the benchmark result should still record wall-clock timing. If trace loading fails, the benchmark result should preserve the trace error and continue producing benchmark JSON and Markdown.

Trace writing should remain in `finally` so failed assessments can still produce partial timing data when possible.

## Testing Strategy

Unit tests should avoid live LLM calls.

Add or update tests for:

- `trace.py`: starting, ending, and serializing node spans.
- `graph.py`: a wrapped fake node records an `ok` span and returns the original result.
- `graph.py`: a wrapped fake node records an `error` span and re-raises the original exception.
- `benchmark.py`: timing summary extraction from a fake trace with LLM calls and node spans.
- `benchmark.py`: timing summary fallback when trace is missing.
- `benchmark.py`: `benchmark_results.json` includes per-result timing.
- `benchmark.py`: `benchmark_report.md` includes timing summary tables.

Suggested test files:

- `tests/test_trace.py`
- `tests/test_graph.py`
- `tests/test_benchmark.py`

## Validation Commands

Run focused tests:

```powershell
uv run python -m pytest tests/test_trace.py tests/test_graph.py tests/test_benchmark.py -q
```

Run the full test suite:

```powershell
uv run python -m pytest -q
```

Run a dry benchmark input check:

```powershell
uv run python benchmark.py --outcome-map CHAARTED:OS --dry-run
```

Run a small real timing benchmark after implementation when API credentials and runtime budget are available:

```powershell
uv run python benchmark.py --outcome-map CHAARTED:OS --input-dir inputs/benchmark --output-dir outputs/benchmark/timing-smoke
```

## Acceptance Criteria

- Existing benchmark accuracy calculations remain unchanged.
- Per-assessment trace JSON includes `node_spans`.
- Each non-skipped benchmark result includes a `timing` object, including failed assessments.
- Benchmark summary includes aggregate timing metrics.
- Benchmark Markdown report includes timing summary tables.
- Tests pass without live LLM calls.
- The implementation is additive and does not alter prompts, provider settings, graph topology, cache keys, or assessment decisions.

## Future Optimization Use

This instrumentation should make later optimization choices data-driven. Examples:

- If LLM latency dominates, compare providers, models, token budgets, caching, and repair rates.
- If `pdf_ingest` dominates, optimize Docling conversion, supplement page windows, or reuse parsed artifacts.
- If RAG dominates, profile embedding/index construction and consider persistent indexes.
- If specific domain SQ nodes dominate, inspect prompt length, retrieval packet size, parse repairs, and provider queue behavior.
- If node spans show branch timing overlap, use trace data to decide whether explicit parallelism or scheduling changes would help.
