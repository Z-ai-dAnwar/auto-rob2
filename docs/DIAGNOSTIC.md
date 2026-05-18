# Diagnostic Runbook

This document covers the trace-instrumented diagnostic workflow for `auto-rob2`: how to capture LLM I/O during a benchmark, run the categorizer, interpret its output, and handle known operational issues.

## When to use this workflow

Use the diagnostic flow when you need to understand *why* the pipeline made a judgment that disagrees with the human reference, not just whether it did. Two recurring questions it answers:

- **RAG-miss vs LLM-miss.** Did retrieval pull the wrong chunks, or did the LLM ignore the right ones?
- **Grounded vs ungrounded LLM answers.** When the LLM produced an answer, can we find that answer in the retrieved chunks, or did it come from training data?

## Workflow

### 1. Run a benchmark with `--no-cache`

```bash
uv run python benchmark.py \
  --outcome-map CHAARTED:OS CHAARTED:PFS \
  --output-dir outputs/benchmark/<run_name> \
  --no-cache
```

`--no-cache` is important for diagnostics: cached responses don't exercise the live LLM and don't surface today's RAG retrieval behavior. The benchmark writes per-trial subdirectories such as `CHAARTED_os/`, each containing:

- `<trial>_rob2_data.json` — full pipeline state including `rag_sources` (retrieved chunks per domain with embedding scores)
- `<trial>_trace.json` — every LLM call's system prompt, user prompt, response, model, tokens, latency, and parse-retry sequences
- `<trial>_rob2_report.md` — human-readable assessment

### 2. Run the categorizer

```bash
uv run python analysis/categorize_failures.py \
  --benchmark-dir outputs/benchmark/<run_name> \
  --output-dir outputs/diagnostic/<run_name>
```

Outputs:

- `diagnostic_summary.csv` — one row per (trial, outcome, domain). Sort or filter by `classification` for triage.
- `diagnostic_report.md` — per-failure detail, with the top 5 retrieved chunks and full LLM responses inline.

### 3. Interpret the classifications

| Classification | Meaning | Typical fix |
|---|---|---|
| `match` | Pipeline matched reference; nothing to investigate. | — |
| `rag_likely_miss` | Either max cosine similarity < 0.3 (chunks unrelated to query) OR the LLM response contained a "no evidence / not reported / cannot determine" phrase. | Improve `DOMAIN_SECTION_FILTERS` or `SQ_QUERIES` for the affected domain. |
| `llm_likely_miss` | Top-3 average cosine >= 0.5 and the LLM did not signal no-evidence. Chunks looked usable; the model misjudged. | Inspect the prompt + decision-table logic; consider deterministic gates for the failing signaling question. |
| `ambiguous` | Mid-range retrieval scores; can't cleanly attribute. | Manual review; sometimes the chunks were borderline. |
| `no_data` | No chunks AND no LLM calls for this domain. Suggests pipeline error upstream. | Check `errors` and `verification_actions` in `_rob2_data.json`. |

### 4. Pay attention to `looks_ungrounded`

For any row classified `llm_likely_miss`, also check `looks_ungrounded`. When True, the LLM's response shares no `>= 20`-character verbatim substring with any of the retrieved chunks for that domain. That is a strong signal the model fell back on its training-data priors instead of citing the evidence it was given. This was the failure mode for the CHAARTED PFS D4 baseline (`4.5=PY` justification "progression assessment relies on subjective clinical judgment" with no chunk overlap), which over-rated D4 from S to High.

`looks_ungrounded` is a coarse heuristic: heavy paraphrasing can also fire it. Treat it as "this row deserves a closer look," not as ground truth.

## Score semantics: L2-squared, not cosine

LangChain's `FAISS.similarity_search_with_score` returns **L2-squared distance** (lower = closer), not cosine similarity. The raw scores in `rag_sources[*].score` therefore look like values in `[0, 2]` where 0 means identical and 2 means orthogonal.

Because the pipeline normalizes embeddings via `encode_kwargs={"normalize_embeddings": True}` in `rag.py`, the identity `L2^2 = 2 - 2*cosine` lets the categorizer recover cosine similarity:

```python
cosine = max(0, 1 - score / 2)
```

Heuristic thresholds (`0.3` for RAG-miss, `0.5` for LLM-miss) apply to the converted cosine value, not the raw score.

If you ever inspect `rag_sources` directly outside the categorizer, remember the raw `score` field is L2-squared. The categorizer's `max_similarity_score` column in `diagnostic_summary.csv` is already converted.

## Known operational issues

### Docling + LangGraph segfault on macOS ARM

Yesterday's diagnostic on the pre-refactor code segfaulted when Docling ran inside a LangGraph-spawned worker on macOS ARM. The 2026-05-16 RAG refactor moved Docling chunking into `pdf_ingest_node`, which runs once on the main thread before any fan-out, and that appears to sidestep the crash. If you still hit a segfault:

1. Set `ROB2_SKIP_DOCLING=1` to take the PyMuPDF4LLM fallback path. Chunking is then unavailable and the pipeline runs on keyword-section extraction.
2. Verify `.python-version` is `3.13` (the pin was reverted from 3.14 because of this issue).

### Anthropic rate limits

Anthropic Tier 1 enforces 50K input tokens per minute, not just RPM. The shared `SlidingWindowRateLimiter` defaults `AnthropicProvider` to 40 RPM and 30K TPM (under the cap for safety). Tune with `ANTHROPIC_RPM_LIMIT` and `ANTHROPIC_TPM_LIMIT`. The provider retries on HTTP 429 with 30-120s exponential backoff.

OpenRouter `:free` tier failures are more varied (queue timeouts, model unavailable, malformed responses), so `OpenRouterProvider` uses a broader retry policy. The asymmetry is intentional.

### XML parse failures from clinical text

Clinical writeups contain phrases like `"<70 years"` and `"P<0.05"`. Raw `<` followed by a digit or space is not a valid XML start, so lxml raises `StartTag: invalid element name` on LLM responses that paraphrase the source. `sanitize_stray_lt` (in `xml_parser.py`) escapes those characters to `&lt;` before parsing, and runs at every `recover=True` parser site (`parse_sq_response`, `extract_tag`, `_parse_paper_evidence_response`, `_nested_text`). If you encounter a new lxml parse error, check whether the responsible LLM response has another unescaped character that the sanitizer doesn't cover yet.

### Filename mismatches

The categorizer expects per-trial subdirectories named `<trial>_<outcome_code>/` (e.g., `CHAARTED_os/`) containing both `<trial>_trace.json` and `<trial>_rob2_data.json` with matching stems. If a benchmark run produced filenames that don't match (e.g., from an interrupted run), `find_run_outputs` may skip those directories silently. Check the stem alignment manually.

### Provider environment

`ROB2_PROVIDER` defaults to `openrouter`. When running an Anthropic-backed benchmark, set `ROB2_PROVIDER=anthropic` *and* `ANTHROPIC_API_KEY` in `.env`. The Anthropic rate-limit env vars only take effect when the provider is actually Anthropic.
