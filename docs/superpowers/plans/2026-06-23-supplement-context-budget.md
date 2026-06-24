# Supplement Context-Overflow Fix - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. FIRST read `docs/adr/0006-bound-supplement-evidence-to-model-context-window.md` (the approved design) - this plan implements it.

**Goal:** Make ARCHES/ENZAMET/STAMPEDE scoreable on gpt-oss-120b (131,072-tok limit) by stopping oversized supplements from being injected wholesale, without regressing the 5 trials that already pass.

**Architecture:** (1) When a supplement does not split into >=3 structural sections, fall back to one segment PER PAGE instead of one whole-document segment, so BM25S retrieves a selective subset. (2) Add guardrails so no single source's text is unbounded and no prompt can exceed the model limit. (3) Re-run k=3 and diff to prove no regression.

**Tech Stack:** Python 3.13, pytest, uv, BM25S supplement retrieval, OpenRouter `openai/gpt-oss-120b`.

**Branch:** `zaid/fix-supplement-context-overflow` (local; ADR-0006 already committed at `5c51a79`). Do NOT touch deterministic judges, skip/NA logic, or the RoB 2 algorithm. Run benchmarks paid via the funded key (`ROB2_PROVIDER=openrouter ROB2_MODEL=openai/gpt-oss-120b`, plus `ROB2_RPD_LIMIT=3000 ROB2_RPM_LIMIT=60` to avoid the requests-per-day stall footgun).

---

## Task 1: Page-level fallback chunking (the root-cause fix)

**Files:**
- Modify: `rob2_pipeline/ingestion/supplement_segments.py` (add `_page_segments`; change `_segments_from_artifact` at lines 163-165)
- Test: `tests/test_supplement_segments.py` (new)

Context: today `_segments_from_artifact` does `if len(structural_segments) < MIN_STRUCTURAL_SEGMENTS: structural_segments = [_full_document_segment(artifact, source)]`. `_full_document_segment` concatenates every page into ONE uncapped segment. `SupplementSegment` fields: `segment_id, document_id, document_name, document_role, source_path, heading, page_numbers, domain_tags, annotation, text`. `ALL_ROB2_DOMAINS = ["D1","D2","D3","D4","D5"]`. Each `artifact.pages` item is a dict with `page_number` and `text`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_supplement_segments.py`:

```python
from rob2_pipeline.ingestion.supplement_segments import _page_segments, ALL_ROB2_DOMAINS


def _source():
    return {
        "document_id": "supp:001",
        "document_name": "protocol.pdf",
        "document_role": "protocol",
        "path": "protocol.pdf",
    }


def test_page_segments_one_per_nonempty_page():
    pages = [{"page_number": i, "text": f"page {i} content"} for i in range(1, 6)]
    segments = _page_segments(pages, _source())
    assert len(segments) == 5
    assert [s.page_numbers for s in segments] == [[1], [2], [3], [4], [5]]
    assert segments[0].text == "page 1 content"
    assert segments[2].heading == "Page 3"
    assert all(s.domain_tags == ALL_ROB2_DOMAINS for s in segments)
    assert all(s.annotation == "" for s in segments)
    # unique, zero-padded segment ids
    assert segments[0].segment_id == "supp:001:segment:0001"
    assert len({s.segment_id for s in segments}) == 5


def test_page_segments_skips_empty_pages():
    pages = [
        {"page_number": 1, "text": "real content"},
        {"page_number": 2, "text": "   "},
        {"page_number": 3, "text": ""},
        {"page_number": 4, "text": "more content"},
    ]
    segments = _page_segments(pages, _source())
    assert [s.page_numbers for s in segments] == [[1], [4]]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_supplement_segments.py -v`
Expected: FAIL with `ImportError: cannot import name '_page_segments'`.

- [ ] **Step 3: Implement `_page_segments`**

Add to `rob2_pipeline/ingestion/supplement_segments.py` (near `_full_document_segment`):

```python
def _page_segments(
    pages: list[dict],
    source: SourceDocument,
) -> list[SupplementSegment]:
    segments: list[SupplementSegment] = []
    for page in pages:
        text = str(page.get("text", "")).strip()
        if not text:
            continue
        page_number = int(page.get("page_number", 0) or 0)
        segment_number = len(segments) + 1
        segments.append(
            SupplementSegment(
                segment_id=(
                    f"{source.get('document_id', 'supplement')}:segment:"
                    f"{segment_number:04d}"
                ),
                document_id=source.get("document_id", ""),
                document_name=source.get("document_name", ""),
                document_role=source.get("document_role", "unknown_supplement"),
                source_path=source.get("path", ""),
                heading=f"Page {page_number}" if page_number else "Page",
                page_numbers=[page_number] if page_number else [],
                domain_tags=list(ALL_ROB2_DOMAINS),
                annotation="",
                text=text,
            )
        )
    return segments
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_supplement_segments.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Wire the fallback to use page segments**

In `_segments_from_artifact`, change the fallback (currently lines ~163-165):

```python
    structural_segments = _structural_segments(artifact, source)
    if len(structural_segments) < MIN_STRUCTURAL_SEGMENTS:
        page_segments = _page_segments(artifact.pages, source)
        structural_segments = page_segments or [_full_document_segment(artifact, source)]
```

(`_full_document_segment` stays as the last-resort for a genuinely single-/zero-text-page document.)

- [ ] **Step 6: Run the full supplement test suite**

Run: `uv run pytest tests/test_supplement_segments.py tests/test_supplement_retrieval.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add rob2_pipeline/ingestion/supplement_segments.py tests/test_supplement_segments.py
git commit -m "fix: page-level fallback for unsegmentable supplements (ADR-0006 change 1)"
```

---

## Task 2: Per-source text cap + token estimator (guardrail)

**Files:**
- Modify: `rob2_pipeline/nodes/evidence_packets.py` (in `_build_packet_for_contract`, after `selected = _select_with_coverage(...)` ~line 173)
- Test: `tests/test_evidence_packet_budget.py` (new)

Context: `_build_packet_for_contract` ranks candidate `PacketSource` dicts (key fields: `text: str`, `score: float`, `matched_terms`, `document_role`) and selects up to 3 via `_select_with_coverage(ranked, contract.coverage_groups, 3)`. A single source's `text` can be huge (a residual whole-document). Cap each selected source's `text` so no one source dominates, keeping the highest-ranked content. No tokenizer exists in the repo; use a conservative char-based estimate.

- [ ] **Step 1: Write the failing test**

Create `tests/test_evidence_packet_budget.py`:

```python
from rob2_pipeline.nodes.evidence_packets import _estimate_tokens, _cap_source_text


def test_estimate_tokens_is_conservative():
    # ~3 chars/token (over-counts tokens vs the observed ~3.6, so it is safe)
    assert _estimate_tokens("a" * 300) >= 100


def test_cap_source_text_truncates_and_marks_long_text():
    src = {"text": "x" * 50000, "score": 1.0}
    capped = _cap_source_text(src, max_chars=6000)
    assert len(capped["text"]) <= 6000 + 40  # body + truncation marker
    assert "truncated" in capped["text"].lower()
    # original dict is not mutated
    assert len(src["text"]) == 50000


def test_cap_source_text_leaves_short_text_unchanged():
    src = {"text": "short evidence", "score": 1.0}
    assert _cap_source_text(src, max_chars=6000)["text"] == "short evidence"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_evidence_packet_budget.py -v`
Expected: FAIL with `ImportError` (functions not defined).

- [ ] **Step 3: Implement the helpers**

Add to `rob2_pipeline/nodes/evidence_packets.py` (module level):

```python
def _estimate_tokens(text: str) -> int:
    # Conservative: ~3 chars/token over-counts tokens vs the observed ~3.6,
    # giving headroom under the model context limit. No tokenizer dependency.
    return len(text) // 3


def _cap_source_text(source: dict, *, max_chars: int) -> dict:
    text = source.get("text", "") or ""
    if len(text) <= max_chars:
        return source
    capped = dict(source)
    capped["text"] = text[:max_chars] + "\n[... source text truncated to fit context ...]"
    return capped
```

- [ ] **Step 4: Apply the cap to selected sources**

In `_build_packet_for_contract`, immediately after `selected = _select_with_coverage(ranked, contract.coverage_groups, 3)`:

```python
    selected = [_cap_source_text(src, max_chars=MAX_SOURCE_CHARS) for src in selected]
```

And add the constant near the top of `evidence_packets.py`:

```python
MAX_SOURCE_CHARS = 8000  # ~2.7k tokens per source; pages are usually well under this
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/test_evidence_packet_budget.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add rob2_pipeline/nodes/evidence_packets.py tests/test_evidence_packet_budget.py
git commit -m "fix: cap per-source evidence text + token estimator (ADR-0006 change 2 guardrail)"
```

---

## Task 3: Config + pre-send total-prompt safety net

**Files:**
- Modify: `rob2_pipeline/config.py` (add `ROB2_PROMPT_TOKEN_BUDGET`)
- Modify: `rob2_pipeline/llm_contracts.py` (in `call_json_contract_llm`, before `provider.complete(...)` ~line 61) and `rob2_pipeline/nodes/common.py` (in `call_node_llm`, before `provider.complete(...)` ~line 122)
- Test: `tests/test_prompt_budget_guard.py` (new)

Context: this is the last-resort guarantee that a prompt can NEVER exceed the model limit. After Tasks 1-2 it should essentially never fire; if it does, it logs LOUDLY (so the no-regression review catches any real evidence loss) and trims the user prompt as a final safety measure. Default budget 115,000 tokens (headroom under 131,072 for schema + instructions + the 2,000-token output).

- [ ] **Step 1: Write the failing test**

Create `tests/test_prompt_budget_guard.py`:

```python
from rob2_pipeline.llm_contracts import _enforce_prompt_budget


def test_under_budget_prompt_is_unchanged():
    prompt = "small prompt"
    out, dropped = _enforce_prompt_budget(prompt, budget_tokens=1000, node="domain1_sq")
    assert out == prompt
    assert dropped == 0


def test_over_budget_prompt_is_trimmed_to_budget():
    prompt = "x" * 600000  # ~200k tokens at 3 chars/token
    out, dropped = _enforce_prompt_budget(prompt, budget_tokens=115000, node="domain4_sq")
    assert len(out) <= 115000 * 3 + 80  # within budget (+marker)
    assert dropped > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_prompt_budget_guard.py -v`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Add the config value**

In `rob2_pipeline/config.py`, add after the other `os.getenv` reads (module level, near line 50):

```python
PROMPT_TOKEN_BUDGET = int(os.getenv("ROB2_PROMPT_TOKEN_BUDGET", "115000"))
```

- [ ] **Step 4: Implement `_enforce_prompt_budget` in `llm_contracts.py`**

```python
import logging

LOGGER = logging.getLogger(__name__)


def _enforce_prompt_budget(prompt: str, *, budget_tokens: int, node: str) -> tuple[str, int]:
    max_chars = budget_tokens * 3  # mirror evidence_packets._estimate_tokens (~3 chars/token)
    if len(prompt) <= max_chars:
        return prompt, 0
    dropped = len(prompt) - max_chars
    LOGGER.warning(
        "PROMPT BUDGET HIT node=%s: trimmed %d chars (~%d tok) to fit budget=%d tok. "
        "Investigate retrieval - evidence may have been lost.",
        node, dropped, dropped // 3, budget_tokens,
    )
    return prompt[:max_chars] + "\n[... prompt trimmed to context budget ...]", dropped
```

- [ ] **Step 5: Call it before sending**

In `call_json_contract_llm` (`llm_contracts.py`), right before `provider.complete(...)`:

```python
    from rob2_pipeline.config import PROMPT_TOKEN_BUDGET
    current_prompt, _ = _enforce_prompt_budget(
        current_prompt, budget_tokens=PROMPT_TOKEN_BUDGET, node=node
    )
    response_obj = provider.complete(system=JSON_SYSTEM_MESSAGE, user=current_prompt)
```

In `call_node_llm` (`rob2_pipeline/nodes/common.py`), right before its `provider.complete(...)` (~line 122), do the same (import `_enforce_prompt_budget` from `rob2_pipeline.llm_contracts`, pass the node name available in that function).

- [ ] **Step 6: Run tests**

Run: `uv run pytest tests/test_prompt_budget_guard.py -v`
Expected: PASS (2 tests).

- [ ] **Step 7: Commit**

```bash
git add rob2_pipeline/config.py rob2_pipeline/llm_contracts.py rob2_pipeline/nodes/common.py tests/test_prompt_budget_guard.py
git commit -m "fix: pre-send prompt token budget safety net (ADR-0006 change 2)"
```

---

## Task 4: Verify on the 3 failing trials + full test suite

**Files:** none (verification)

- [ ] **Step 1: Run the full unit suite**

Run: `uv run pytest -q`
Expected: PASS (no regressions in existing tests).

- [ ] **Step 2: Single-trial smoke on the worst offender (ENZAMET)**

```bash
ROB2_PROVIDER=openrouter ROB2_MODEL=openai/gpt-oss-120b ROB2_RPD_LIMIT=3000 ROB2_RPM_LIMIT=60 \
uv run python benchmark.py --outcome-map ENZAMET:OS \
  --use-supplements --supplement-dir inputs/benchmark/supplement --no-cache \
  --output-dir outputs/benchmark/fixcheck_enzamet
```
Expected: completes (no HTTP 400). Confirm a `*_rob2_data.json` is written under `outputs/benchmark/fixcheck_enzamet/ENZAMET_os/`.

- [ ] **Step 3: Confirm prompts are now bounded**

Inspect the new trace's largest prompt:
```bash
uv run python -c "import json,glob; \
f=glob.glob('outputs/benchmark/fixcheck_enzamet/ENZAMET_os/*_trace.json')[0]; \
d=json.load(open(f,encoding='utf-8')); \
print(max((c.get('input_tokens') or 0) for c in d['llm_calls']))"
```
Expected: max input tokens well under 131072 (target < ~115000). If still over, the pre-send guard prevented the crash but evidence was trimmed - check the WARNING logs and tighten `MAX_SOURCE_CHARS` / retrieval before proceeding.

---

## Task 5: No-regression re-run (k=3) + report

**Files:** scoring tool at `docs/superpowers/tooling/parse_k3.py` (committed alongside this plan).

- [ ] **Step 1: Run k=3 on all 8 trials**

For run in 1,2,3, into `outputs/benchmark/fixed_gptoss_k3_run{1,2,3}`:
```bash
ROB2_PROVIDER=openrouter ROB2_MODEL=openai/gpt-oss-120b ROB2_RPD_LIMIT=3000 ROB2_RPM_LIMIT=60 \
uv run python benchmark.py --outcome-map ARASENS:OS ARCHES:OS CHAARTED:OS ENZAMET:OS LATITUDE:OS PEACE-1:OS STAMPEDE:OS TITAN:OS \
  --use-supplements --supplement-dir inputs/benchmark/supplement --no-cache \
  --output-dir outputs/benchmark/fixed_gptoss_k3_run1
```
(Run the 3 sequentially, or in parallel with separate output dirs; watch for sustained 429s and fall back to sequential. ~14-20 min/trial.)

- [ ] **Step 2: Score and compare to the pre-fix baseline**

Adapt `docs/superpowers/tooling/parse_k3.py` to point at `fixed_gptoss_k3_run{1,2,3}` and run it. Compare against the pre-fix numbers (D1 93 / D2 87 / D3 67 / D4 100 / D5 80 on the 5-trial set; ARCHES/ENZAMET/STAMPEDE previously FAILED). Acceptance: all 8 now score; the 5 previously-passing trials are unchanged or improved.

- [ ] **Step 3: Write results to the outbox + update CODING-STATE**

Append a dated `DONE:` entry to `claude-sync/state/mailbox/outbox-mayo.md` with the new 8-trial per-domain agreement + variance and the before/after. Update `claude-sync/state/CODING-STATE.md`. Commit + push claude-sync. Do NOT push the feature branch to Ali or open a PR without Zaid's explicit ok.

---

## Self-review notes (for the executor)

- ADR-0006 coverage: Change 1 = Task 1; Change 2 = Tasks 2-3; no-regression gate = Tasks 4-5. All spec sections map to a task.
- The exact JSON-serialized evidence injection that dominates the SQ prompt was NOT fully traced this session (planner was context-limited). Task 1 should shrink it structurally (page-sized sources instead of whole-document). Task 4 Step 3 is the checkpoint: if ENZAMET's max prompt is still near/over the limit after Task 1, trace where the bulk comes from (read the largest `user_prompt` block in the trace, grep for where that block is assembled) and tighten before the k=3 re-run. The pre-send guard (Task 3) prevents a crash regardless, but its WARNING firing means evidence was trimmed and must be investigated.
- Keep the deterministic judges, skip/NA logic, and RoB 2 algorithm untouched.
