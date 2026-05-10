# Spec: Domain Node Evidence Priority Fix

**Date:** 2026-05-10
**Status:** Proposed

## Context

Benchmark run on CHAARTED:OS scored 2/6 (D3 ✓, D4 ✓; D1 ✗, D2 ✗, D5 ✗, Overall ✗).
All failures were over-flagging: pipeline returned "Some concerns" where ground truth is "Low".

Root-cause analysis identified a single inverted-priority pattern in every domain node:

```python
# BUG: if RAG returns anything, structured evidence is silently discarded
randomization_text = rag_contexts.get("d1") or format_evidence(evidence["d1_randomization"])
baseline_text      = "" if rag_contexts.get("d1") else format_evidence(evidence["baseline_table"])
consort_text       = "" if rag_contexts.get("d1") else format_evidence(evidence["consort_flow"])
```

When FAISS returned any result (even a single generic sentence), the domain-specific
extracted sections were bypassed entirely and supplementary sections were zeroed out.

### Failure trace

| Domain | Structured section | Key content (correct answer) | RAG returned | SQ result |
|--------|--------------------|------------------------------|--------------|-----------|
| D1 | `d1_randomization` | "Allocation sequence and concealment were managed by the ECOG-ACRIN Statistical Center" | "Patients were assigned to ADT alone or ADT plus docetaxel" | 1.1=NI, 1.2=NI → Some concerns |
| D2 | `d2_blinding` | "The trial was open-label; no masking of participants, investigators, or outcome assessors was performed" | generic ITT sentence | 2.1=NI, 2.2=NI → Some concerns |
| D5 | `d5_registration` | "The protocol and statistical analysis plan were publicly available; primary and secondary endpoints were prespecified" | registration text (present but prompt too strict) | 5.1=PN → Some concerns |

D3 and D4 returned correctly because RAG happened to surface the right sentences.
The fix must apply to all domains for consistency.

---

## Design

### Fix 1 — Always-merge prompt construction

**Principle:** Structured evidence sections are domain-targeted LLM extractions — they are
always primary. RAG is supplementary general retrieval — it is always appended, never replacing.

**Change pattern applied identically to all 5 domain node files:**

Before:
```python
some_text  = rag_contexts.get("key") or format_evidence(evidence["section"])
other_text = "" if rag_contexts.get("key") else format_evidence(evidence["other"])
```

After:
```python
some_text  = format_evidence(evidence["section"])
other_text = format_evidence(evidence["other"])
rag_text   = rag_contexts.get("key", "")
```

**Prompt template structure added to all 5 domain prompts in `prompts.py`:**

```
=== PRIMARY EVIDENCE (domain-extracted — treat as authoritative) ===
{domain_section_text}
{supplementary_section_text}

=== ADDITIONAL RETRIEVED CONTEXT (full-document search) ===
{rag_text}
```

Instruction to include in each prompt: *"The Primary Evidence section was extracted
specifically for this domain. Use it as your primary source. The Additional Retrieved
Context supplements it — it may contain supporting detail not present in the primary
section."*

**Generalisation:** If a structured section is empty, both blocks are sparse and NI
remains the correct answer. If the section is populated, the primary block surfaces it
regardless of what RAG returns.

---

### Fix 2 — D5 SQ 5.1 prompt calibration

SQ 5.1 asks: *"Was the result analysed in accordance with a pre-specified plan?"*

For CHAARTED the LLM answered PN citing incomplete SAP detail in the paper, despite
evidence stating the protocol and SAP were publicly available and endpoints were
prespecified. The RoB 2 guidance does not require every statistical detail to be
reprinted in the paper.

**Guidance to add to `PROMPT_DOMAIN5` for SQ 5.1:**

> Answer **Y** (or **PY**) for SQ 5.1 if:
> (a) a trial registration number is cited (NCT, ISRCTN, EUDRACT, etc.) AND the
> registration predates the primary analysis; OR
> (b) the paper explicitly states that primary endpoints or the statistical analysis
> plan were prespecified or publicly available.
>
> Do NOT require that every statistical detail (covariate list, imputation method,
> sensitivity analyses) be reprinted in the paper itself. A registration number
> combined with a prespecification claim is sufficient for Y.
>
> Answer **PN** only if there is specific evidence that the analysis plan was modified
> after data unblinding, or if no registration exists and no prespecification is
> documented anywhere.

---

## Files to Modify

| File | Change |
|------|--------|
| `rob2_pipeline/nodes/domain1.py` | Remove short-circuit; pass `randomization_text`, `baseline_text`, `consort_text`, `rag_text` separately |
| `rob2_pipeline/nodes/domain2.py` | Same for all 3 sub-nodes: `sq12`, `conditional`, `analysis` |
| `rob2_pipeline/nodes/domain3.py` | Apply consistent always-merge pattern |
| `rob2_pipeline/nodes/domain4.py` | Apply consistent always-merge pattern |
| `rob2_pipeline/nodes/domain5.py` | Same; route `registered_endpoint` and `ctgov_outcomes` to primary block |
| `rob2_pipeline/prompts.py` | Add two-block structure to D1–D5 templates; add D5 SQ 5.1 calibration guidance |

**Not in scope:** `rag.py`, `rag_queries.py`, judges, `pdf_ingestion.py`, `registration_api.py`

---

## Verification

```bash
uv run python benchmark.py --outcome-map CHAARTED:OS --output-dir outputs/benchmark/chaarted
```

Expected `benchmark_report.md` after fix:

| Trial | Outcome | D1 | D2 | D3 | D4 | D5 | Overall |
|-------|---------|----|----|----|----|-----|---------|
| CHAARTED:OS | Overall Survival | Y | Y | Y | Y | Y | Y |

Regression check: D3 and D4 must remain Y.
