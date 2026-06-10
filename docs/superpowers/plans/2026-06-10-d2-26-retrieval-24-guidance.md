# D2 2.6 retrieval re-aim + 2.4 amendment guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stabilize Domain 2 by aiming SQ 2.6's retrieval at the analysis-population statement and correcting the SQ 2.4 reasoning that mistakes a design-level protocol amendment for a per-participant deviation.

**Architecture:** Two small, independent, general changes upstream of the deterministic Sterne judge. Change 1 edits `SQ_QUERIES["2.6"]` so the intention-to-treat / analysed-as-randomized sentence reliably enters 2.6's retrieval candidate pool (the existing `ANALYSIS_POPULATION_COVERAGE_TERMS` coverage slot then protects it, and the existing Y/PY inference guidance reads it). Change 2 appends a clarifying sentence to the SQ 2.4 PN `ResponseRule` so a protocol amendment to trial design is not treated as an outcome-affecting deviation. No change to judges, `sq_control.py`, 2.5, or 2.3.

**Tech Stack:** Python, pytest, `.venv\Scripts\python.exe`. Spec: `docs/superpowers/specs/2026-06-10-d2-26-retrieval-24-guidance-design.md`.

---

### Task 1: Re-aim SQ 2.6 retrieval queries (Change 1, primary)

**Files:**
- Modify: `rob2_pipeline/rag_queries.py` (the `SQ_QUERIES["2.6"]` list)
- Test: `tests/test_rag_queries.py`

**Context:** 2.6's current queries are all SAP/pre-specification flavored ("statistical analysis plan adherence", "analysis method as pre-specified", "deviation from planned statistical method", "primary analysis method"). None targets the analysis-population statement, so the ITT sentence enters the candidate pool only by luck -> 2.6 flips Y<->NI. We ADD analysis-population queries; we KEEP the existing ones (additive). Mirror the existing d5 content-assertion pattern (`test_domain_queries_d5_returns_sq5_queries_and_sap_terms`).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_rag_queries.py`:

```python
def test_sq26_queries_target_analysis_population_statement():
    """SQ 2.6 must retrieve the analysis-population (ITT / analysed-as-assigned)
    statement, not only statistical-analysis-plan / pre-specification text."""
    joined = " ".join(SQ_QUERIES["2.6"]).lower()
    assert "intention-to-treat" in joined or "intention to treat" in joined
    assert "assigned" in joined  # "...analysed in the group to which they were assigned"
    assert "all randomized" in joined or "all randomised" in joined
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_rag_queries.py::test_sq26_queries_target_analysis_population_statement -v`
Expected: FAIL (current 2.6 queries contain none of these phrases).

- [ ] **Step 3: Write minimal implementation**

In `rob2_pipeline/rag_queries.py`, extend `SQ_QUERIES["2.6"]` (keep the existing four entries, append these three):

```python
    "2.6": [
        "statistical analysis plan adherence",
        "analysis method as pre-specified",
        "deviation from planned statistical method",
        "primary analysis method",
        "all randomized participants were included in the analysis",
        "patients analysed in the group to which they were assigned",
        "intention-to-treat population analysed",
    ],
```

- [ ] **Step 4: Run the new test and the full rag_queries suite**

Run: `.venv\Scripts\python.exe -m pytest tests/test_rag_queries.py -v`
Expected: PASS, including `test_sq_queries_each_sq_has_at_least_three_queries` and `test_domain_queries_d2_returns_sq2_queries` (the latter builds its expected set from `SQ_QUERIES`, so it stays consistent).

- [ ] **Step 5: Commit**

```bash
git add rob2_pipeline/rag_queries.py tests/test_rag_queries.py
git commit -m "D2 2.6: aim retrieval queries at the analysis-population statement"
```

---

### Task 2: SQ 2.4 amendment guidance (Change 2)

**Files:**
- Modify: `rob2_pipeline/methodology/domain2.py` (the `"2.4"` `RuleCard`, PN `ResponseRule`)
- Test: `tests/test_domain2_d3_inference.py`

**Context:** In the failing run, 2.4 was answered PY citing "sample size was increased after protocol amendments" -- a design-level amendment, not a per-participant deviation. We append a clarifying sentence to the PN rule (the answer the model should land on when the only cited "deviation" is a design amendment). The classifier sees `ResponseRule` text via `build_decision_table` -> `row["rule"]`, which is what the helper `_json_path_rules` reads, so the test asserts on the rule the model actually consumes. General methodology, no trial named.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_domain2_d3_inference.py` (helper `_json_path_rules` already exists at top of file):

```python
def test_d2_sq24_pn_excludes_design_amendment_from_deviations():
    rules = _json_path_rules("2.4")
    pn = rules["PN"].lower()
    assert "amendment" in pn
    assert "design" in pn or "not a per-participant deviation" in pn
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python.exe -m pytest tests/test_domain2_d3_inference.py::test_d2_sq24_pn_excludes_design_amendment_from_deviations -v`
Expected: FAIL (current PN rule says only "Deviations were minimal or unlikely to influence the assessed outcome.").

- [ ] **Step 3: Write minimal implementation**

In `rob2_pipeline/methodology/domain2.py`, the `"2.4"` `RuleCard`, replace the PN `ResponseRule` text:

```python
                "PN": ResponseRule(
                    "Deviations were minimal or unlikely to influence the assessed outcome. "
                    "A protocol amendment to trial design (e.g., a change to sample size, "
                    "eligibility, or concomitant therapy permitted across all arms) is a "
                    "design change, not a per-participant deviation from intended "
                    "intervention, and on its own does not make deviations likely to affect "
                    "the outcome."
                ),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python.exe -m pytest tests/test_domain2_d3_inference.py::test_d2_sq24_pn_excludes_design_amendment_from_deviations -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rob2_pipeline/methodology/domain2.py tests/test_domain2_d3_inference.py
git commit -m "D2 2.4: clarify a design-level protocol amendment is not a deviation"
```

---

### Task 3: Full-suite regression gate + guard verification (STOP before benchmark)

**Files:** none modified (verification only).

**Context:** Both changes are LLM-facing surfaces; the real proof is the k>=3 benchmark, which is a spend gate held for Zaid. This task confirms nothing regressed at the unit level and that the guard reasoning still holds in code, then STOPS.

- [ ] **Step 1: Run the entire unit suite**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: all pass. Baseline before these tasks was 491 passed; expect 493 (the two new tests). No failures, no errors.

- [ ] **Step 2: Confirm the protected surfaces are untouched**

Run: `git diff --stat 8bf1571 HEAD -- rob2_pipeline/judges/ rob2_pipeline/nodes/sq_control.py`
Expected: empty output (no changes to the deterministic judge or skip/NA logic).

- [ ] **Step 3: Confirm scope discipline (only the four intended files changed since the spec commit)**

Run: `git diff --name-only 8bf1571 HEAD`
Expected exactly:
```
rob2_pipeline/methodology/domain2.py
rob2_pipeline/rag_queries.py
tests/test_domain2_d3_inference.py
tests/test_rag_queries.py
```
(The uncommitted `rob2_pipeline/llm_contracts.py` + `tests/test_llm_contracts.py` fence fix stays out of these commits, as before.)

- [ ] **Step 4: STOP and hand back to Zaid**

Do NOT run the benchmark. Report: tests green (count), the 4-file diff, and that the ENZAMET/TITAN guard is structurally intact (ENZAMET 2.3=N -> 2.4 NA / 2.6 already Y; neither change can move it). Wait for Zaid's go-ahead on the k>=3 benchmark (free tier + watchdog) per the spec's acceptance test.

---

## Self-review notes
- **Spec coverage:** Change 1 -> Task 1; Change 2 -> Task 2; acceptance-test step 1 (unit) -> Task 3; guard -> Task 3 step 2/4; out-of-scope (2.5, 2.3, judges) enforced by Task 3 step 3 diff check. k>=3 benchmark is the post-plan spend gate, intentionally not a task.
- **No placeholders:** every code/test block is literal.
- **Type/name consistency:** `_json_path_rules`, `SQ_QUERIES`, `ANALYSIS_POPULATION_COVERAGE_TERMS`, `build_decision_table` all match the existing codebase symbols verified during planning.
- **No push / no AI attribution** in any commit, per project rules.
