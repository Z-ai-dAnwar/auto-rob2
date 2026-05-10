# Spec: D4/D5 Domain Reasoning Fix for PFS and Composite Endpoints

**Date:** 2026-05-10  
**Status:** Proposed

---

## Context

Benchmark run on CHAARTED (OS + PFS) reveals two domain-level failures on the PFS outcome that
drive a wrong overall judgment (pipeline: High, reference: Low). D1–D3 agree exactly; only D4 and
D5 fail.

| Domain | Reference | Pipeline | Match |
|--------|-----------|----------|-------|
| D4 | Some concerns | Low | ✗ |
| D5 | Low | High | ✗ |
| Overall | Low | High | ✗ |

Evidence files:
- `outputs/benchmark/chaarted/CHAARTED_pfs/CHAARTED_rob2_data.json`
- `outputs/benchmark/chaarted/benchmark_results.json`

The reference CSV (`data/references/progression_free_survival.csv`) shows D4="Some concerns" for
7 of 10 PFS trials, confirming these are systematic failures, not CHAARTED-specific edge cases.

---

## Failure 1: D4 Under-flagged (pipeline=Low, reference=Some concerns)

### Decision path

PFS signaling answers sent to `judge_domain4` (`rob2_pipeline/judges/domain4.py`):

| SQ | Answer | Problem |
|----|--------|---------|
| 4.1 | N | Correct |
| 4.2 | N | Correct |
| 4.3 | NI | Caused by empty `evidence.d2_blinding` for PFS |
| 4.4 | N | **Wrong** — LLM quoted OS definition ("time to death") for a PFS run |
| 4.5 | NA | Correct |

Judge fires line 18–19:
```python
# s41=N, s42=N, s43=NI, s44=N → Low
if s41 in ("N","PN","NI") and s42 in ("N","PN") and s43 in ("Y","PY","NI") and s44 in ("N","PN"):
    return "Low", "..."
```

For D4=Some concerns we need Q4.4=Y/PY, which fires line 25:
```python
# s43=Y/PY/NI, s44=Y/PY/NI, s45=N/PN → Some concerns
if ... s44 in ("Y","PY","NI") and s45 in ("N","PN"):
    return "Some concerns", "..."
```

### Root cause

**Q4.4 ("Is the assessment of the outcome likely to have been influenced by knowledge of
intervention received?") was answered N using the OS outcome definition.**

The `evidence.d4_outcome_meas` section leads with:
> *"Overall survival was defined as time from randomization to death from any cause."*

The LLM anchors to this sentence even when the assessed outcome is PFS. Death is objective; the
LLM concludes Q4.4=N. But PFS in CHAARTED is a composite subjective endpoint:
> *"biochemical, symptomatic, or radiographic progression with testosterone ≤50 ng/dL"*

Assessor awareness of treatment assignment CAN influence judgment of disease progression. The
correct answer is Q4.4=PY, giving D4=Some concerns (matching reference).

**Secondary issue:** `evidence.d2_blinding` is empty for PFS. Without blinding text the LLM
cannot confirm open-label status for Q4.3. This is a contributing factor but not the primary
driver (Q4.4=N is the decisive error).

---

## Failure 2: D5 Over-flagged (pipeline=High, reference=Low)

### Decision path

| SQ | Answer | Problem |
|----|--------|---------|
| 5.1 | Y | Correct |
| 5.2 | PY | **Wrong** — composite endpoint definition misread as selective measurement |
| 5.3 | N | Correct |

Judge fires line 7 immediately:
```python
if s52 in ("Y", "PY") or s53 in ("Y", "PY"):
    return "High", "..."
```

For D5=Low we need Q5.2=N, which fires line 9:
```python
if s51 in ("Y","PY") and s52 in ("N","PN") and s53 in ("N","PN"):
    return "Low", "..."
```

### Root cause

**Q5.2 ("Is the result likely to have been selected from multiple eligible outcome measurements
within the outcome domain?") was answered PY because the LLM confused a composite endpoint
definition with selective outcome reporting.**

LLM reasoning (verbatim from `CHAARTED_rob2_data.json`):
> "Several possible progression definitions exist (biochemical, symptomatic, radiographic), and
> the reported HR combines them, suggesting possible selective reporting."

This is a categorical misclassification:

| Concept | Q5.2 answer |
|---------|------------|
| **Composite endpoint** — multiple criteria combined into one pre-specified measure a priori | N — this is not selection |
| **Selective reporting** — choosing the most favourable of several separately pre-specified single measurements after seeing data | Y/PY |

CHAARTED pre-specified its composite PFS definition in the registered protocol (NCT00309985)
before unblinding. Combining progression criteria is not post-hoc selection.

**Contributing factor:** `registered_endpoint` = "Not reported" for the PFS run (vs. "Overall
survival" for OS). The preliminary node / ClinicalTrials.gov API is not surfacing PFS as a
registered secondary endpoint, leaving the LLM with less pre-specification evidence for Q5.1/5.2.

---

## Design

Three targeted prompt fixes. The deterministic judge logic in `domain4.py` and `domain5.py`
is correct; only the upstream LLM answer generation needs to change.

### Fix A: Outcome-aware D4 prompt (targets Q4.4)

In the D4 signaling-question prompt (`rob2_pipeline/prompts.py`), add an explicit instruction:

1. Identify which outcome is currently being assessed (injected as `{outcome}`).
2. When the `d4_outcome_meas` evidence section contains definitions for multiple outcomes,
   answer based only on the definition for `{outcome}`.
3. Apply this reasoning rule for Q4.4:
   - Hard endpoints (death, all-cause mortality, vital status) → Q4.4=N (objective, knowledge
     of assignment cannot influence the result)
   - Composite or investigator-assessed progression endpoints (biochemical/symptomatic/
     radiographic progression, response rate, time-to-event with subjective components) →
     Q4.4=PY in an open-label trial, unless there is explicit evidence of blinded adjudication

### Fix B: Composite-endpoint guidance for D5 prompt (targets Q5.2)

In the D5 signaling-question prompt, add a clarifying note for Q5.2:

> A composite endpoint (e.g., PFS defined as biochemical OR symptomatic OR radiographic
> progression combined into a single pre-specified measure) is NOT multiple eligible outcome
> measurements. Answer Q5.2=N for composite endpoints unless there is evidence that specific
> components were selected post-hoc.
>
> Answer Q5.2=Y/PY only when the paper reports one specific scale or time point chosen from
> several separately pre-specified alternatives (e.g., "PFS at 12 months" chosen over "PFS at
> 6 months" or "median PFS").

### Fix C: Secondary endpoint lookup for `registered_endpoint` (targets Q5.1/D5 evidence)

In `rob2_pipeline/nodes/preliminary.py`, when the assessed outcome does not match the primary
registered endpoint, also search `registered_secondary_endpoints` and `ctgov_outcomes` for a
match. If found, set `registered_endpoint` to the matched secondary endpoint name so the D5
prompt has pre-specification confirmation for secondary outcomes.

---

## Files to Modify

| File | Change | Type |
|------|--------|------|
| `rob2_pipeline/prompts.py` | Add outcome-type instruction to D4 prompt; add composite-endpoint note to D5 Q5.2 prompt | Modify |
| `rob2_pipeline/nodes/domain4.py` | Pass `state["outcome"]` and `state["outcome_type"]` into D4 prompt | Modify |
| `rob2_pipeline/nodes/domain5.py` | Pass `state["outcome"]` and `state["outcome_type"]` into D5 prompt | Modify |
| `rob2_pipeline/nodes/preliminary.py` | Search secondary endpoints when primary doesn't match assessed outcome | Modify |
| `tests/test_prompts.py` | Add tests verifying outcome-type instruction is in D4/D5 prompts | Modify |
| `tests/test_graph.py` | Add integration test: PFS composite endpoint → D5=Low, D4=Some concerns | Modify |

---

## Implementation Steps

- [ ] **Step 1: Write failing tests**
  - `tests/test_prompts.py`: assert D4 prompt contains `outcome_type` variable and objective/
    subjective guidance text
  - `tests/test_prompts.py`: assert D5 prompt contains composite-endpoint clarification for Q5.2
  - `tests/test_graph.py`: mock PFS run with composite endpoint → assert D4="Some concerns",
    D5="Low"
  - Run: `uv run pytest tests/test_prompts.py tests/test_graph.py -x` → expect failures

- [ ] **Step 2: Fix D4 prompt — outcome-aware Q4.4 guidance**
  - In `rob2_pipeline/prompts.py`, locate the D4 SQ prompt template
  - Add `{outcome}` and `{outcome_type}` template variables
  - Add explicit instruction block distinguishing objective (death) vs. composite/subjective
    (progression) endpoints for Q4.4
  - In `rob2_pipeline/nodes/domain4.py`, inject `state["outcome"]` and `state["outcome_type"]`
    when formatting the D4 prompt
  - Run: `uv run pytest tests/test_prompts.py -x` → expect Step 1 prompt tests to pass

- [ ] **Step 3: Fix D5 prompt — composite endpoint note for Q5.2**
  - In `rob2_pipeline/prompts.py`, locate the D5 SQ prompt template
  - Add the composite-endpoint clarification paragraph above the Q5.2 question
  - In `rob2_pipeline/nodes/domain5.py`, inject `state["outcome"]` and `state["outcome_type"]`
  - Run: `uv run pytest tests/test_prompts.py -x` → expect Step 1 prompt tests to pass

- [ ] **Step 4: Fix secondary endpoint lookup in preliminary node**
  - In `rob2_pipeline/nodes/preliminary.py`, after setting `registered_endpoint`, add fallback:
    if the assessed outcome is not the primary endpoint, search
    `registered_secondary_endpoints` and `ctgov_outcomes` for a match and update
    `registered_endpoint` accordingly
  - Add unit test verifying secondary endpoint surfacing
  - Run: `uv run pytest tests/ -x`

- [ ] **Step 5: Full test suite + benchmark**
  - `uv run pytest tests/` → all green
  - `uv run python benchmark.py --outcome-map CHAARTED:OS CHAARTED:PFS --input-dir inputs/benchmark --output-dir outputs/benchmark/chaarted`
  - Verify `outputs/benchmark/chaarted/benchmark_results.json`:
    - CHAARTED:PFS D4 = Some concerns ✓
    - CHAARTED:PFS D5 = Low ✓
    - CHAARTED:PFS Overall = Low ✓
    - CHAARTED:OS all domains unchanged ✓

---

## Verification Checklist

- [ ] `uv run pytest tests/` passes with no regressions
- [ ] CHAARTED:PFS D4 matches reference (Some concerns)
- [ ] CHAARTED:PFS D5 matches reference (Low)
- [ ] CHAARTED:PFS Overall matches reference (Low)
- [ ] CHAARTED:OS 6/6 agreement unchanged
- [ ] D4 prompt contains outcome-type instruction
- [ ] D5 prompt contains composite-endpoint clarification
