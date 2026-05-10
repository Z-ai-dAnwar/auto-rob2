# Spec: Benchmark Accuracy Improvements — All Remaining Failures

**Date:** 2026-05-11
**Status:** Proposed
**Extends:** `2026-05-10-d2-d4-prompt-accuracy-fixes.md` (Fixes A–F; B partially implemented)

---

## Context

After running the full 3-trial benchmark (CHAARTED, PEACE-1, STAMPEDE), aggregate accuracy is
**70% domain-level (28/40 judgments) and 50% overall (4/8 outcomes)**.  Prior spec Fix B landed
(CHAARTED D2 = 100%), but Fixes A/C–F were not applied; PEACE-1 and STAMPEDE introduced five
new failure patterns the prior spec did not address.

All fixes below are grounded in Sterne et al. 2019 (main paper + supplement).  No fix is
motivated solely by matching a specific benchmark verdict — each maps to a stated principle in
the official guidance.

Anti-overfitting constraint: the 7 unrun trials in the reference CSVs are a held-out blind test
set.  No prompt change may be written to match a specific benchmark verdict that is not also
defensible by RoB 2 guidance wording.

---

## Current Accuracy

| Domain | CHAARTED | PEACE-1 | STAMPEDE | Aggregate |
|--------|----------|---------|----------|-----------|
| D1     | 2/2 100% | 2/3  67% | 3/3 100% | 7/8  88%  |
| D2     | 2/2 100% | 0/3   0% | 3/3 100% | 5/8  63%  |
| D3     | 2/2 100% | 3/3 100% | 0/3   0% | 5/8  63%  |
| D4     | 1/2  50% | 2/3  67% | 1/3  33% | 4/8  50%  |
| D5     | 2/2 100% | 1/3  33% | 2/3  67% | 5/8  63%  |
| Overall| 2/2 100% | 1/3  33% | 0/3   0% | 3/8  38%  |

---

## Root-Cause Failure Analysis

### RC-1 — PEACE-1 D2 (0%): Q2.3 = N despite protocol amendment

The pipeline answers Q2.3=N for all three PEACE-1 outcomes.  Reference is "Some concerns."

**Ground-truth rationale (reviewer-provided):**
> "PEACE-1 trial raised some concerns over the deviation from intended intervention considering the
> trial protocol was modified to include docetaxel for some patients owing to change in standard of
> care."

The docetaxel protocol amendment IS a trial-context deviation: a formal change to the experimental
arm's standard-of-care constitutes an "additional intervention administered to some participants
because of trial participation" (supplement p.7).  The current Q2.3 guidance covers routine
non-adherence but says nothing about formal protocol amendments that alter systemic therapy.

**Correct SQ path:** Q2.3=**NI** → D2 Part1 = Some concerns (via algorithm).

The supplement (p.7) explicitly states: *"The answer 'No information' may be appropriate, because
trialists do not always report whether deviations arose because of the trial context."* The
PEACE-1 protocol amendment was driven by an external change in standard of care; the report does
not clarify whether the amendment was necessitated specifically by trial context or by the external
SOC pressure. This genuine uncertainty warrants NI — not Y/PY (which would require knowing the
amendment arose *from* trial participation), and not N (which would require knowing it was
consistent with non-trial clinical practice). NI → D2=Some concerns per the algorithm. ✓

---

### RC-2 — STAMPEDE D3 (0%): Q3.1 = Y despite ≥10% missing participants

The pipeline answers Q3.1=Y ("nearly complete data") for all three STAMPEDE outcomes, skipping
Q3.2–3.4 entirely.  Reference is "Some concerns."

**Ground-truth rationale (reviewer-provided):**
> "For STAMPEDE, LATITUDE, and ARCHES some concerns were raised for potential missing outcome data
> in at least 10% of the total population."

Q3.1 asks whether data are available for "all or nearly all" participants.  "Nearly all" is a
calibrated threshold; ≥10% missing outcome data falls below it.  The existing spec added Q3.4
cancer-censoring guidance (Fix C) but that guidance is unreachable when Q3.1=Y causes the cascade
to short-circuit.

The STAMPEDE assessments answer Q3.1=Y on the basis of ITT completeness language, but do not
verify whether the analysis population equals the randomised population within a 10% margin.

---

### RC-3 — STAMPEDE D4 PFS/AE (33%): Q4.2 = Y/PY for differential visit frequency

Pipeline gives D4=High for STAMPEDE PFS and AE because Q4.2=Y/PY ("measurement differed between
groups").  Reference is "Some concerns."

**Ground-truth rationale:**
> "Some concerns were raised for trials assessing progression free survival and adverse events
> which followed an open-label design and did not mask the outcome assessment."

The open-label path to D4=Some concerns runs through Q4.3 (assessors aware) → Q4.4 (could be
influenced) → Q4.5=N/PN (standardised criteria, not *likely* influenced) → Some concerns.

The pipeline is instead triggering on Q4.2 because it flags differential assessment *frequency*
(combination arm assessed more often than ADT-alone arm) as "differential ascertainment between
groups."  Supplement p.22 Q4.2 covers differential measurement *method, criteria, scale, or
threshold* — not visit frequency.  More frequent visits in one arm increase detection opportunity
but do not change the measurement instrument or criteria.

**Correct SQ path:** Q4.1=N, Q4.2=N/PN (frequency ≠ method), Q4.3=PY (open-label), Q4.4=PY
(PFS/AE require judgment), Q4.5=PN (standardised criteria without known strong beliefs) →
D4=Some concerns.

---

### RC-4 — PEACE-1 PFS D5 (33%): LLM reports OS statistics when assessing PFS

Pipeline gives D5=High for PEACE-1 PFS because Q5.2=Y: "Several eligible time-to-event outcomes
were pre-specified, yet the assessed result (HR 0.82 for overall survival) was selected from among
them."  HR 0.82 is the *OS* result, not the PFS result.  The LLM confused which outcome it was
assessing.  Reference is Low.

The root cause is that the D5 prompt does not contain a clear instruction to restrict attention to
the *assessed outcome* only.  In a paper reporting both OS and PFS, the LLM can conflate the two
when reasoning about selective reporting.

---

### RC-5 — PEACE-1 D1 OS (67%): inconsistent Q1.2 extraction across outcomes

Pipeline gives D1=High for PEACE-1 OS (Q1.2=N) but D1=Low for PEACE-1 PFS/AE (Q1.2=Y), from
the same PDF.

The OS assessment extracted: *"accessible only to the trial data manager and later to each
investigator"* → interpreted as allocation NOT concealed.

The PFS assessment extracted: *"Randomisation was performed via the Tenalea autonomous software
solely accessed by the trial data manager"* → interpreted as allocation concealed (correct).

The RAG retrieval pulled different text passages for the two runs.  The OS passage uses the phrase
"accessible only to" which the model misread as insufficient concealment, even though "accessible
only to [role X]" precisely describes restricted access — the definition of concealment.

---

## Prior Spec Status (Fixes A–F)

| Fix | Content | Status |
|-----|---------|--------|
| A | `PROMPT_PRELIMINARY_INFO`: exclude composite endpoints from `vital-status` | **Not yet applied** (CHAARTED D4 PFS still Low; should be Some concerns) |
| B | `PROMPT_DOMAIN2_CONDITIONAL`: Q2.3 NI→N/PN for routine non-starts | **Implemented** (CHAARTED D2 = 100%) |
| C | `PROMPT_DOMAIN3`: Q3.4 cancer-censoring guidance | **Not yet applied** (unreachable until RC-2 Fix H lands) |
| D | `PROMPT_DOMAIN4`: Q4.3 open-label inference rule | **Not yet applied** (CHAARTED D4 PFS still Low) |
| E | `PROMPT_DOMAIN4`: Q4.4 N restricted to vital-status outcomes | **Not yet applied** |
| F | `PROMPT_DOMAIN4`: Q4.5 Some concerns vs High calibration | **Not yet applied** |

Fixes A, C–F must land together to fix CHAARTED D4 PFS; they are a prerequisite for the
STAMPEDE D4 fix (RC-3 / Fix I) to produce Some concerns rather than High.

---

## Proposed Changes

### Fix A — `PROMPT_PRELIMINARY_INFO`: outcome_type excludes composite endpoints  *(carry-forward)*

**File:** `rob2_pipeline/prompts.py`, `<outcome_type>` block (~line 69–75)

Rewrite `vital-status` definition to require death as the *sole* event criterion:
> "`vital-status`: all-cause mortality or disease-specific mortality assessed as a **single
> criterion** — death is the only event.  Do **not** use for composite endpoints that combine
> death with non-mortality criteria such as progression, relapse, or hospitalisation, even if
> death is one component."

Add examples:
> "Examples: OS (all-cause death) = `vital-status`; PFS (progression or death) =
> `clinician-composite`; CRPC (biochemical/symptomatic/radiographic progression) =
> `clinician-composite`; RECIST response = `clinician-graded`."

**Source:** Supplement p.22 Q4.4 — distinguishes "all-cause mortality (no judgment)" from
outcomes requiring judgment.

---

### Fix C — `PROMPT_DOMAIN3`: Q3.4 cancer-specific censoring guidance  *(carry-forward)*

**File:** `rob2_pipeline/prompts.py`, `PROMPT_DOMAIN3`, Q3.4 block (~line 538–545)

Add cancer-specific censoring rationale for reason 5 (supplement p.19):
> "In time-to-event analyses, follow-up is censored when participants stop or change their
> assigned intervention — for example because of drug toxicity or, **in cancer trials, when
> participants switch to second-line chemotherapy or a salvage regimen**.  Switching to
> second-line therapy is itself an outcome-related event (it indicates treatment failure or
> disease progression), so censoring at that point is outcome-dependent."

Also add: "Check whether censoring rates differ between groups — a meaningful difference supports
answering Y or PY."

**Source:** Supplement p.19 Q3.4 reason 5 (verbatim).

---

### Fix D — `PROMPT_DOMAIN4`: Q4.3 open-label inference rule  *(carry-forward)*

**File:** `rob2_pipeline/prompts.py`, `PROMPT_DOMAIN4`, Q4.3 block (~line 611–617)

Add inference rule:
> "Inference rule: if the trial is open-label (Q2.1=Y as shown above) and the report contains no
> mention of a central blinded adjudication committee or independent blinded assessors, answer PY
> rather than NI.  Reserve NI for cases where assessor blinding status genuinely cannot be
> inferred — unusual once Q2.1=Y is established."

Narrow NI definition from "assessor awareness is not reported" to "assessor awareness is not
reported **and cannot be inferred from any available evidence**."

**Source:** Supplement p.22 Q4.3 (NI defined strictly); main paper p.3 NI principle.

---

### Fix E — `PROMPT_DOMAIN4`: Q4.4 N restricted to vital-status outcomes  *(carry-forward)*

**File:** `rob2_pipeline/prompts.py`, `PROMPT_DOMAIN4`, Q4.4 block (~line 621–628)

Rewrite N definition:
> "N applies only to `vital-status` outcomes (all-cause or disease-specific mortality).  The
> supplement states knowledge of assignment is 'unlikely to influence observer-reported outcomes
> that do not involve judgement, for example all-cause mortality.'  For `clinician-composite`
> and `clinician-graded` outcomes in open-label trials, N is almost never appropriate.  For
> composite progression endpoints (PFS, TTP, CRPC) that include symptomatic or radiographic
> components, answer PY unless explicit evidence shows all criteria are mechanical and
> judgment-free."

**Source:** Supplement p.22 Q4.4 (verbatim language incorporated).

---

### Fix F — `PROMPT_DOMAIN4`: Q4.5 Some concerns vs High calibration  *(carry-forward)*

**File:** `rob2_pipeline/prompts.py`, `PROMPT_DOMAIN4`, Q4.5 block (~line 631–636)

Add calibration guidance:
> "High requires strong levels of belief in either beneficial or harmful effects — for example,
> patient-reported symptoms in homeopathy trials, or recovery assessed by the physiotherapist who
> delivered the intervention.  In standard open-label oncology trials with pre-specified
> radiographic/clinical progression criteria applied by independent assessors, answer N or PN
> (→ Some concerns), not Y or PY (→ High)."

Rewrite PN definition:
> "PN: little evidence of likely influence; standardised radiographic or clinical criteria applied
> by independent assessors with no known strong prior beliefs; typical open-label oncology
> context."

**Source:** Supplement p.23 Q4.5 elaboration.

---

### Fix G — `PROMPT_DOMAIN2_CONDITIONAL`: Q2.3 NI for protocol amendments  *(new)*

**File:** `rob2_pipeline/prompts.py`, `PROMPT_DOMAIN2_CONDITIONAL`, Q2.3 block (~line 269–277)

Add after the current N/PN examples:
> "**Protocol amendments mid-trial:** When a formal protocol amendment added or changed a
> systemic therapy in one or both arms owing to an **external change in standard of care** (e.g.,
> docetaxel or abiraterone becoming standard after regulatory approval mid-enrolment), score
> **NI** for Q2.3. The supplement (p.7) explicitly states: 'The answer "No information" may be
> appropriate, because trialists do not always report whether deviations arose because of the
> trial context.' Amendments driven by external SOC changes are genuinely ambiguous — the report
> typically does not clarify whether the amendment was necessitated by trial context or purely
> external forces. NI → D2=Some concerns via the algorithm. Do NOT score Y/PY (which requires
> knowing the deviation arose *from* trial participation) or N/PN (which requires knowing the
> change was consistent with non-trial clinical practice)."

Also add an evidence-scope reminder:
> "**Evidence scope for Q2.3:** Protocol amendment history is often reported in the registration/
> protocol section (d5_registration) rather than the blinding section. Always review
> d5_registration and protocol notes for amendment records when assessing Q2.3."

Strengthen the existing NI-as-last-resort reminder:
> "NI is appropriate only when deviations are described that *could plausibly* have arisen from
> the trial context but the report does not clarify their origin. Do not answer NI merely because
> routine clinical events (non-starts, minor dose adjustments) lack an explicit statement that
> they were unrelated to trial context — those belong to N/PN."

**Source:** Supplement p.7 Q2.3: *"The answer 'No information' may be appropriate, because
trialists do not always report whether deviations arose because of the trial context"*; main
paper p.3 NI principle.

---

### Fix H — `PROMPT_DOMAIN3`: Q3.1 completeness threshold  *(new)*

**File:** `rob2_pipeline/prompts.py`, `PROMPT_DOMAIN3`, Q3.1 block (~line 490–510)

Add explicit completeness calculation requirement and threshold:
> "Before answering, calculate the percentage of randomised participants whose outcome data are
> included in the analysis: `(analysis N / randomised N) × 100`.  If **≥ 10% of randomised
> participants are excluded from or absent in the analysis**, answer N or PN — do not answer Y or
> PY.  'Nearly all' in the context of RoB 2 means typically < 5–10% missing; the reviewer
> literature treats ≥ 10% as the threshold for D3 concern.  Report this calculation in the
> `<completeness>` field."

Add for time-to-event outcomes:
> "For time-to-event outcomes: participants who are administratively censored at end-of-follow-up
> are NOT missing.  Participants who are censored early because they withdrew, were lost to
> follow-up, or switched treatments are potentially missing.  If the proportion of non-event
> censorings appears large relative to observed events (e.g., > 20% of participants without
> event), investigate whether this is informative censoring before answering Y."

**Source:** Reviewer rationale explicitly states ≥ 10% threshold.  Cochrane handbook D3 guidance
distinguishes administrative censoring from informative loss-to-follow-up.

---

### Fix I — `PROMPT_DOMAIN4`: Q4.2 passive detection bias vs. active protocol assessments  *(new)*

**File:** `rob2_pipeline/prompts.py`, `PROMPT_DOMAIN4`, Q4.2 block (~line 593–602)

**Important constraint on judge behaviour:** The D4 judge returns `High` directly when Q4.2=Y/PY
(`rob2_pipeline/judges/domain4.py` line 12), without proceeding to Q4.3–Q4.5.  This is correct
per the algorithm — genuine differential ascertainment of the outcome is a systematic measurement
bias.  Fix I must therefore ensure the LLM answers N/PN for cases that are NOT genuine differential
ascertainment.

Add clarification to the Q4.2 block distinguishing the two types covered by Q4.2:

> "Q4.2 covers **two** types of differential ascertainment — and the distinction matters because
> Y/PY leads directly to High:
>
> **1. Passive detection bias** (→ Y/PY): One arm has more unscheduled clinical contacts than
> the other, creating additional opportunities for events to be *passively* identified during
> routine care.  The supplement (p.21–22) explicitly cites 'additional visits to a healthcare
> provider, leading to additional opportunities for outcome events to be identified' as a Q4.2=Y
> scenario.  Answer Y or PY when passive, context-dependent detection genuinely differs between
> arms.
>
> **2. Active protocol-specified assessments** (→ N/PN): Both arms undergo the **same**
> pre-specified outcome assessments — same imaging modality, same criteria, same protocol-defined
> schedule — but treatment-administration visit frequency happens to differ.  The extra visits are
> treatment visits, not additional outcome-assessment occasions.  When measurement method, criteria,
> and schedule are identical for both arms, the ascertainment procedure does not differ between
> groups.  Answer N or PN.
>
> Rule: If the trial uses a pre-specified assessment protocol (e.g., CT/MRI every 8–12 weeks,
> PSA every 3 months, CTCAE grading at each cycle visit) applied identically to both arms,
> answer N or PN even if one arm attends clinic more frequently for treatment administration.
> Reserve Y/PY for cases where the detection method, criteria, or passive contact opportunity
> genuinely differs between groups."

**Source:** Supplement p.21–22 Q4.2 elaboration (both the passive-detection example and the
general "same measurement methods and thresholds, used at comparable time points" standard).

---

### Fix J — `PROMPT_DOMAIN5`: outcome-specific focus instruction  *(new)*

**File:** `rob2_pipeline/prompts.py`, `PROMPT_DOMAIN5`, header or Q5.2 block (~line 694–705)

Add an explicit scope restriction in the prompt header:
> "IMPORTANT: You are assessing Domain 5 for the specific outcome: **{outcome}**.  All three
> questions concern whether the **{outcome}** result was selectively reported.  Do NOT reason about
> whether other outcomes (e.g., OS when you are assessing PFS, or PFS when assessing OS) were
> selectively reported or chosen.  Each outcome is assessed independently."

Add to Q5.2 N/PN definition:
> "Pre-specified co-primary endpoints are not 'multiple eligible outcome measurements' relative to
> each other — both are pre-specified and both are expected to be reported.  A paper reporting both
> OS and PFS when both are co-primary endpoints does not constitute selective outcome selection for
> either endpoint."

**Source:** Supplement p.28 Q5.2 — selective selection from "multiple eligible outcome
measurements" refers to choosing among equivalent measures of the same construct, not reporting
pre-specified co-primaries.

---

### Fix K — `PROMPT_DOMAIN1`: Q1.2 restricted access = concealment  *(new)*

**File:** `rob2_pipeline/prompts.py`, `PROMPT_DOMAIN1`, Q1.2 block (~line 145–165)

Extend the Y/PY evidence list with restricted-access phrasing:
> "Also score Y or PY when the report describes restricted access to the allocation list using any
> of these patterns: 'accessible only to [role]', 'only [role] had access to the allocation
> sequence', '[role] alone maintained the randomisation list', 'allocation was not disclosed until
> after enrolment' — these all describe concealment through information restriction, which is a
> valid concealment mechanism even if no sealed envelope or telephone system is mentioned."

Add a contrast example:
> "Do NOT confuse 'accessible only to the data manager (and later to investigators after
> enrolment)' with 'not concealed' — disclosure to investigators *after* enrolment is the
> expected post-randomisation unblinding; it does not imply the allocation was known *before*
> enrolment."

**Source:** Supplement p.4 Q1.2 — concealment includes "allocation not disclosed until after
enrolment" as a valid mechanism; central data-manager control is functionally equivalent.

---

## Architectural Change: Outcome-Agnostic D1 Evidence

The Q1.2 inconsistency (RC-5) arises because RAG retrieval can return different text passages for
the same trial on different outcome assessment runs.  In addition to Fix K (prompt guidance), the
D1 retrieval context should use only outcome-*independent* evidence.

**Change:** In `rob2_pipeline/nodes/domain1.py`, the D1 node already uses
`evidence["d1_randomization"]` as primary evidence (extracted once from the PDF during ingestion).
Ensure the RAG context passed to D1 (`rag_contexts["d1"]`) uses retrieval queries that do NOT
include the assessed outcome name.  The current `rag_queries.py` D1 queries appear outcome-agnostic
(they query for "allocation sequence randomization", "concealment", etc.) — verify this is still
the case and add a note in the query set documenting that D1 queries must remain outcome-agnostic.

If needed: add a `trial_level` flag to D1/D2 SQ nodes that signals to the caller that these
answers should be consistent across outcomes; the benchmark runner can log a warning when the same
trial returns different Q1.1/Q1.2 answers for different outcomes (detection, not prevention).

---

## Expected Improvements (per benchmark trial)

| Failure → Fix | Trial | Domain | Before | Expected after |
|---------------|-------|--------|--------|---------------|
| RC-1 + Fix G  | PEACE-1 | D2 | 0/3 0% | 3/3 100% |
| RC-2 + Fix H  | STAMPEDE | D3 | 0/3 0% | 3/3 100% |
| RC-3 + Fixes I,D,E,F | STAMPEDE | D4 | 1/3 33% | 3/3 100% (OS=Low, PFS/AE=Some concerns match ref) |
| RC-4 + Fix J  | PEACE-1 | D5 | 1/3 33% | 2–3/3 67–100% |
| RC-5 + Fix K  | PEACE-1 | D1 | 2/3 67% | 3/3 100% |
| Fixes A,D,E,F | CHAARTED/PEACE-1 | D4 | 50–67% | 3/3 100% (PFS outcome_type corrects cascade) |

These expectations are directional; actual results depend on model behaviour.  The 7 held-out
trials provide an unbiased evaluation after implementation.

---

## Files to Modify

| File | Changes |
|------|---------|
| `rob2_pipeline/prompts.py` | Fixes A, C–K (10 prompt-text edits) |
| `rob2_pipeline/rag_queries.py` | Verify D1 queries are outcome-agnostic; add comment |
| `rob2_pipeline/nodes/domain1.py` | Optional: add inconsistency detection log |
| `tests/test_prompts.py` | Update tests for changed prompt sections |

No changes to judge logic, state schema, or core graph flow.

---

## Implementation Steps

- [ ] **Step 1:** Apply Fix A to `PROMPT_PRELIMINARY_INFO` (`outcome_type` block)
- [ ] **Step 2:** Apply Fix G to `PROMPT_DOMAIN2_CONDITIONAL` (Q2.3 protocol amendment)
- [ ] **Step 3:** Apply Fix H to `PROMPT_DOMAIN3` (Q3.1 completeness threshold)
- [ ] **Step 4:** Apply Fix C to `PROMPT_DOMAIN3` (Q3.4 cancer censoring — carry-forward)
- [ ] **Step 5:** Apply Fix I to `PROMPT_DOMAIN4` (Q4.2 frequency ≠ method)
- [ ] **Step 6:** Apply Fix D to `PROMPT_DOMAIN4` (Q4.3 open-label inference rule)
- [ ] **Step 7:** Apply Fix E to `PROMPT_DOMAIN4` (Q4.4 vital-status restriction)
- [ ] **Step 8:** Apply Fix F to `PROMPT_DOMAIN4` (Q4.5 calibration)
- [ ] **Step 9:** Apply Fix J to `PROMPT_DOMAIN5` (outcome-specific focus)
- [ ] **Step 10:** Apply Fix K to `PROMPT_DOMAIN1` (Q1.2 restricted access = concealment)
- [ ] **Step 11:** Verify `rag_queries.py` D1 queries are outcome-agnostic
- [ ] **Step 12:** Update `tests/test_prompts.py` to cover new guidance text
- [ ] **Step 13:** Run `uv run pytest tests/` — no regressions
- [ ] **Step 14:** Re-run full 3-trial benchmark; compare before/after accuracy table

---

## Verification Checklist

- [ ] `uv run pytest tests/` passes with no regressions
- [ ] `outcome_type` vital-status definition excludes composite endpoints; examples present
- [ ] Q2.3 N definition covers routine non-starts (existing Fix B)
- [ ] Q2.3 guidance explicitly covers formal protocol amendments (external SOC) → NI; references d5_registration as evidence source
- [ ] Q3.1 includes ≥10% threshold and completeness calculation requirement
- [ ] Q3.4 includes cancer second-line chemotherapy censoring example
- [ ] Q4.2 guidance distinguishes passive detection bias (Y/PY) from active protocol-specified assessments (N/PN); includes judge constraint note
- [ ] Q4.3 open-label inference rule present (NI narrowed)
- [ ] Q4.4 N definition restricted to vital-status outcomes
- [ ] Q4.5 oncology calibration present (Some concerns vs High)
- [ ] D5 prompt header contains outcome-specific focus instruction
- [ ] D5 Q5.2 co-primary endpoints clarification present
- [ ] Q1.2 restricted-access patterns listed; contrast example present
- [ ] D1 RAG queries verified as outcome-agnostic
- [ ] Full 3-trial benchmark re-run shows improvement in all 5 root-cause domains
