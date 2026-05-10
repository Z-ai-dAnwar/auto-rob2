# Spec: Prompt Calibration for All 5 RoB 2 Domains (Grounded in Sterne et al. 2019)

**Date:** 2026-05-10  
**Status:** Proposed

---

## Context

After the D4/D5 fixes landed (`spec/pfs-d4-d5-reasoning-fix`), the CHAARTED benchmark shows D5
in perfect agreement on both outcomes. Two failures remain on the PFS outcome:

| Domain  | Reference           | Pipeline                      | Direction      |
| ------- | ------------------- | ----------------------------- | -------------- |
| D2      | Low                 | Some concerns                 | False positive |
| D4      | Some concerns       | Low                           | False negative |
| Overall | Low (PFS), Low (OS) | Some concerns (PFS), Low (OS) | PFS wrong      |

The user provided the following published reviewer rationale as ground truth:

> "Risk of bias was assessed using Cochrane risk of bias for randomized controlled trials
> guidelines (v2) for each trial across patient important outcomes (overall survival, progression
> free survival, and grade 3 or higher adverse events). Overall bias for each trial was deemed to
> be low if there were low risk of bias in all domains or some concerns in one domain. PEACE-1
> trial raised some concerns over the deviation from intended intervention considering the trial
> protocol was modified to include docetaxel for some patients owing to change in standard of
> care. For STAMPEDE, LATITUDE, and ARCHES some concerns were raised for potential missing outcome
> data in at least 10% of the total population. Some concerns were raised for trials assessing
> progression free survival and adverse events which followed an open-label design and did not mask
> the outcome assessment. Only four trials followed a double-blind design. The outcome assessment
> for overall survival was deemed to be void of any potential biases due to unblinded assessment."

This spec grounds all proposed changes in the official Sterne et al. 2019 RoB 2 paper and
supplementary material (question elaborations), which is the canonical source for RoB 2 algorithm
guidance. Three systematic rules emerge from the reviewer rationale:

| Rule   | Domain | Condition                                                             | Reference judgment                                 |
| ------ | ------ | --------------------------------------------------------------------- | -------------------------------------------------- |
| **R1** | D2     | Protocol formally modified due to external change in standard of care | Some concerns                                      |
| **R2** | D4     | Open-label design + PFS or AE outcome (no masked outcome assessment)  | Some concerns                                      |
| **R3** | D4     | OS outcome in any design                                              | Low (objective, unblinded assessment void of bias) |

---

## Judge Verification

All 5 domain judge functions and the overall judge have been verified against the official
algorithm tables in the Sterne supplement. **No judge changes are required.** All bugs are
upstream in the LLM prompts.

| Judge    | File                              | Verification                   |
| -------- | --------------------------------- | ------------------------------ |
| D1       | `rob2_pipeline/judges/domain1.py` | Correct per supplement pp.4–5  |
| D2 (ITT) | `rob2_pipeline/judges/domain2.py` | Correct per supplement pp.9–10 |
| D3       | `rob2_pipeline/judges/domain3.py` | Correct per supplement pp.20   |
| D4       | `rob2_pipeline/judges/domain4.py` | Correct per supplement p.24    |
| D5       | `rob2_pipeline/judges/domain5.py` | Correct per supplement p.29    |
| Overall  | `rob2_pipeline/judges/overall.py` | Correct per main paper Table 3 |

---

## Failure Analysis

### Failure 1 — D2 PFS False Positive (pipeline=Some concerns, reference=Low)

**Decision path:**

| SQ  | Answer | Notes                      |
| --- | ------ | -------------------------- |
| 2.1 | Y      | Open-label trial           |
| 2.2 | Y      | Correct                    |
| 2.3 | **NI** | **Wrong** — should be N/PN |
| 2.6 | Y      | ITT used                   |

`_part1()` fires on Q2.3=NI → `"Part1 Some concerns"`. Part2=Low (Q2.6=Y). Combined = **Some concerns**.

**Root cause:** Q2.3=NI from over-broad NI defaulting when the only described events are routine
pre-treatment non-starts ("6 patients in combination group did not start therapy"). The supplement
(p.7) is explicit:

> _"Answer 'No' or 'Probably no' if there were changes from assigned intervention that are
> inconsistent with the trial protocol, such as non-adherence to intervention, but these are
> consistent with what could occur outside the trial context."_

The LLM uses NI because the report lacks an explicit statement that the non-starts were unrelated
to trial context. But the supplement (and main paper p.3) both say NI is a last resort, not a
default for absent statements:

> _"The 'no information' response should be used only when insufficient details are available to
> allow a different response, and when, in the absence of these details, it would be unreasonable
> to respond 'probably yes' or 'probably no.'"_

Routine pre-treatment non-starts are the paradigmatic example of deviations consistent with what
could occur outside the trial → N/PN is not unreasonable → NI is wrong.

### Failure 2 — D4 PFS False Negative (pipeline=Low, reference=Some concerns)

**Decision path:**

| SQ  | Answer | Notes                                                        |
| --- | ------ | ------------------------------------------------------------ |
| 4.1 | N      | Correct                                                      |
| 4.2 | N      | Correct                                                      |
| 4.3 | **NI** | Wrong — open-label trial, assessors are aware (should be PY) |
| 4.4 | **N**  | Wrong — PFS requires judgment; only OS/death warrants N      |
| 4.5 | NA     | Skipped because Q4.4=N                                       |

**Root cause — three stacked issues:**

1. **`outcome_type = "vital-status"` misclassification.** PFS (time to biochemical, symptomatic,
   or radiographic progression) is a `clinician-composite` endpoint. The preliminary_info prompt
   does not clearly exclude composite endpoints from `vital-status`, so the LLM anchors to the
   "death" component. This deprives the D4 prompt of endpoint-type context.

2. **Q4.3 = NI in open-label trial (should be PY).** The D4 prompt passes `Q2.1 participants
aware of assignment: Y` but does not instruct the LLM to infer assessor awareness from this.
   The supplement (p.22) reserves NI only for genuinely unknown assessor blinding — which is
   unusual once Q2.1=Y is established and no blinded adjudication committee is mentioned.

3. **Q4.4 = N with OS reasoning applied to PFS.** The LLM justifies Q4.4=N with "the outcome is
   inherently objective." The supplement (p.22) is explicit:
   > _"Knowledge of the assigned intervention could influence participant-reported outcomes (such
   > as level of pain), observer-reported outcomes involving some judgement, and intervention
   > provider decision outcomes. They are unlikely to influence observer-reported outcomes that do
   > not involve judgement, for example all-cause mortality."_
   > Death = objective → N correct for OS. PFS requires radiographic and symptomatic judgment →
   > N is wrong; PY is correct.

---

## All Proposed Changes

### Fix A — `PROMPT_PRELIMINARY_INFO`: Exclude composite endpoints from `vital-status`

**File:** `rob2_pipeline/prompts.py`, `<outcome_type>` block (lines ~69–75)

Rewrite the `vital-status` definition to require death as the sole criterion, and add examples:

> "`vital-status`: all-cause mortality or disease-specific mortality assessed as a **single
> criterion** — death is the only event that counts. Do **not** use this category for composite
> endpoints that combine death with non-mortality criteria such as progression, relapse, or
> hospitalisation, even if death is one component."

Add examples line:

> "Examples: OS (all-cause death) = `vital-status`; PFS (progression or death) =
> `clinician-composite`; CRPC (biochemical, symptomatic, or radiographic progression) =
> `clinician-composite`; RECIST response rate = `clinician-graded`."

**Source:** Supplement p.22 Q4.4 distinguishes "all-cause mortality" (no judgment) from
outcomes involving judgment; this distinction requires correct outcome_type classification.

---

### Fix B — `PROMPT_DOMAIN2_CONDITIONAL`: Strengthen Q2.3 N/PN vs NI + add NI reminder

**File:** `rob2_pipeline/prompts.py`, `PROMPT_DOMAIN2_CONDITIONAL` (lines ~269–277)

1. Add NI-as-last-resort reminder before the questions.

2. Strengthen the `N` definition to explicitly cover routine pre-treatment non-starts:

   > "Routine pre-treatment non-starts — a small number of participants in the experimental arm
   > who do not begin the assigned therapy before the first dose for clinical reasons such as
   > performance status decline, patient preference, or comorbidity — are normal clinical
   > management events; score N or PN, not NI, unless the report specifically attributes them to
   > trial-context factors (e.g., differential monitoring, unblinding-driven off-protocol care, or
   > a formal protocol amendment driven by an external change in standard of care)."

3. Narrow the `NI` definition to require genuine uncertainty about deviations that actually
   occurred:
   > "Use only when deviations are described that could plausibly have arisen from trial context
   > but the report does not clarify their origin — for example, when it is unclear whether a
   > formal protocol amendment or external standard-of-care change drove the deviation. NI is a
   > last resort: do not answer NI merely because routine non-adherence events lack an explicit
   > statement that they were unrelated to trial context."

**Source:** Supplement p.7 Q2.3 elaboration; main paper p.3 NI principle.

**Note on PEACE-1:** The strengthened N definition explicitly exempts formal protocol amendments
driven by an external change in standard of care — exactly the PEACE-1 D2 scenario. The fix
therefore preserves PEACE-1=Some concerns while correcting CHAARTED=Low.

---

### Fix C — `PROMPT_DOMAIN3`: Q3.4 cancer-specific censoring guidance

**File:** `rob2_pipeline/prompts.py`, `PROMPT_DOMAIN3`, Q3.4 block (lines ~538–545)

Add cancer-specific censoring guidance, citing the supplement directly:

> "Per the RoB 2 supplement, five specific reasons support answering Y: (1) differences between
> groups in proportions of missing outcome data; (2) reported reasons for missingness provide
> evidence of outcome-dependence; (3) reported reasons differ between groups; (4) trial
> circumstances make outcome-dependent missingness likely; (5) in time-to-event analyses,
> participants' follow-up is censored when they stop or change their assigned intervention — for
> example because of drug toxicity or, **in cancer trials, when participants switch to second-line
> chemotherapy**. In cancer trials, switching to second-line therapy is itself an outcome-related
> event (it indicates treatment failure or progression), so censoring at that point is
> outcome-dependent."

Also add: "For time-to-event outcomes, check whether rates of censoring differ between
intervention groups — a difference in censoring rates supports answering Y or PY."

**Source:** Supplement p.19 Q3.4 reason 5 (verbatim).

**Why this matters:** STAMPEDE, LATITUDE, and ARCHES all had ≥10% missing outcome data. The
reviewer rationale cited this explicitly. Reason 5 from the supplement explains why D3=Some
concerns in cancer trials with treatment switching. This fix is grounded in official guidance,
not benchmarks.

---

### Fix D — `PROMPT_DOMAIN4`: Q4.3 open-label inference rule

**File:** `rob2_pipeline/prompts.py`, `PROMPT_DOMAIN4`, Q4.3 block (lines ~611–617)

Add an inference rule after the bullet definitions:

> "Inference rule: If the trial is open-label (Q2.1=Y as shown in the context above) and the
> report contains no mention of a central blinded outcome adjudication committee or independent
> blinded assessors, answer PY (assessors likely aware of assignment) rather than NI. Reserve NI
> for cases where the blinding status of outcome assessors genuinely cannot be inferred — which
> is unusual once Q2.1=Y is established."

Also narrow the NI definition from "assessor awareness is not reported" to "assessor awareness
is not reported **and cannot be inferred from any available evidence**."

**Source:** Supplement p.22 Q4.3 (NI defined strictly); main paper p.3 NI principle.

---

### Fix E — `PROMPT_DOMAIN4`: Q4.4 endpoint-type rule

**File:** `rob2_pipeline/prompts.py`, `PROMPT_DOMAIN4`, Q4.4 block (lines ~621–628)

Rewrite the `N` definition with an explicit endpoint-type rule:

> "N applies only when the outcome is physiologically determined and cannot be influenced by
> assessor knowledge — specifically `vital-status` outcomes (all-cause or disease-specific
> mortality). The supplement explicitly states that knowledge of intervention assignment is
> 'unlikely to influence observer-reported outcomes that do not involve judgement, for example
> all-cause mortality.' For `clinician-composite` and `clinician-graded` outcomes in open-label
> trials, N is almost never appropriate. For composite progression endpoints (PFS, TTP, CRPC)
> that include symptomatic or radiographic components, answer PY in an open-label trial unless
> explicit evidence shows all progression criteria are mechanical and judgment-free."

**Source:** Supplement p.22 Q4.4 elaboration (verbatim language incorporated).

---

### Fix F — `PROMPT_DOMAIN4`: Q4.5 calibration (Some concerns vs High)

**File:** `rob2_pipeline/prompts.py`, `PROMPT_DOMAIN4`, Q4.5 block (lines ~631–636)

Add calibration guidance to distinguish Some concerns from High:

> "This question distinguishes 'could have been influenced' (Some concerns, Q4.5=N/PN) from
> 'likely was influenced' (High, Q4.5=Y/PY/NI). Per the supplement, High requires strong levels
> of belief in either beneficial or harmful effects of the intervention — for example,
> patient-reported symptoms in trials of homeopathy, or assessments of recovery by a
> physiotherapist who delivered the intervention. In standard open-label oncology trials with
> pre-specified radiographic/clinical progression criteria applied by independent assessors,
> answer N or PN (Some concerns), not Y or PY."

Rewrite `PN` definition:

> "PN: little evidence of likely influence; standardized radiographic or clinical criteria
> applied by independent assessors with no known strong prior beliefs; typical open-label
> oncology trial context."

**Source:** Supplement p.23 Q4.5 elaboration (verbatim examples incorporated).

**Why this matters:** Without this fix, the pipeline may escalate open-label PFS to D4=High
rather than Some concerns, which is wrong per the reviewer rationale and per the supplement.

---

## Scope: Other Benchmark Failures These Fixes Predict

| Trial                          | Domain | Reason                                                                         | Expected reference |
| ------------------------------ | ------ | ------------------------------------------------------------------------------ | ------------------ |
| PEACE-1                        | D2     | Protocol modified to include docetaxel (change in standard of care)            | Some concerns      |
| STAMPEDE                       | D3     | ≥10% missing outcome data + cancer-trial censoring (reason 5, supplement p.19) | Some concerns      |
| LATITUDE                       | D3     | ≥10% missing outcome data + cancer-trial censoring                             | Some concerns      |
| ARCHES                         | D3     | ≥10% missing outcome data + cancer-trial censoring                             | Some concerns      |
| All open-label trials (PFS/AE) | D4     | No masked outcome assessment (Rule R2)                                         | Some concerns      |
| All trials                     | D4     | OS outcome — objective, no judgment (Rule R3)                                  | Low                |

---

## Files to Modify

| File                       | Changes                         |
| -------------------------- | ------------------------------- |
| `rob2_pipeline/prompts.py` | 6 prompt-text edits (Fixes A–F) |

No changes to judge logic, state model, graph, or test infrastructure.

---

## Implementation Steps

- [ ] **Step 1: Update `PROMPT_PRELIMINARY_INFO`** — apply Fix A to `<outcome_type>` block
- [ ] **Step 2: Update `PROMPT_DOMAIN2_CONDITIONAL`** — apply Fix B to Q2.3 guidance
- [ ] **Step 3: Update `PROMPT_DOMAIN3`** — apply Fix C to Q3.4 guidance
- [ ] **Step 4: Update `PROMPT_DOMAIN4`** — apply Fix D to Q4.3 guidance
- [ ] **Step 5: Update `PROMPT_DOMAIN4`** — apply Fix E to Q4.4 guidance
- [ ] **Step 6: Update `PROMPT_DOMAIN4`** — apply Fix F to Q4.5 guidance
- [ ] **Step 7: Run test suite** — `uv run pytest tests/` → no regressions expected
- [ ] **Step 8: Re-run CHAARTED benchmark** — verify PFS D2=Low, D4=Some concerns, Overall=Low;
      verify OS all-domain agreement unchanged

---

## Verification Checklist

- [ ] `uv run pytest tests/` passes with no regressions
- [ ] CHAARTED:PFS D2 matches reference (Low)
- [ ] CHAARTED:PFS D4 matches reference (Some concerns)
- [ ] CHAARTED:PFS Overall matches reference (Low)
- [ ] CHAARTED:OS 6/6 agreement unchanged
- [ ] `vital-status` definition excludes composite endpoints; examples present
- [ ] D2 Q2.3 N definition covers routine pre-treatment non-starts
- [ ] D2 Q2.3 NI definition is narrowed to require genuine uncertainty
- [ ] D3 Q3.4 includes cancer-trial second-line chemotherapy censoring guidance
- [ ] D4 Q4.3 contains open-label inference rule
- [ ] D4 Q4.4 N definition restricted to vital-status outcomes with supplement citation
- [ ] D4 Q4.5 contains Some concerns vs High calibration with supplement examples
