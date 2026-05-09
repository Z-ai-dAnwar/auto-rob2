# RoB 2 Assessment

## Trial information
- **Trial:** Androgen-deprivation therapy (ADT) plus docetaxel (75 mg/m² every 3 weeks for six cycles) vs Androgen-deprivation therapy (ADT) alone
- **Experimental intervention:** Androgen-deprivation therapy (ADT) plus docetaxel (75 mg/m² every 3 weeks for six cycles)
- **Comparator:** Androgen-deprivation therapy (ADT) alone
- **Outcome assessed:** Overall Survival
- **Numerical result:** HR 0.61 (95% CI 0.47 to 0.80)
- **Effect of interest:** Effect of assignment to intervention (intention-to-treat)
- **Sources consulted:** abstract, methods, randomization, blinding, outcomes, analysis, results, missing_data, registration, baseline, consort, supplementary

## Domain 1: Bias arising from the randomization process

| Question | Answer | Supporting quote | Justification |
|----------|--------|-----------------|---------------|
| 1.1 Was the allocation sequence random? | NI | "Patients were randomly assigned to ADT alone or to combination therapy with ADT plus docetaxel..." (randomization_section) | The report states that random assignment occurred but does not describe the specific random sequence generation method. |
| 1.2 Was the allocation sequence concealed? | NI | "Patients were randomly assigned to ADT alone or to combination therapy..." (randomization_section) | No details are provided about how allocation was concealed from enrolling personnel. |
| 1.3 Did baseline differences suggest a problem? | N | "Baseline Characteristics... Age, race, ECOG status, volume of metastases, Gleason score, PSA level, prior treatment... are comparable between groups" (baseline_characteristics) | The baseline table shows balanced groups with no substantial differences that would suggest a problem with randomization. |

**Domain 1 judgment: Some concerns**
**Algorithm rationale:** Row: Any / NI / N-PN-NI -> Some concerns (concealment unclear)

## Domain 2: Bias due to deviations from intended interventions

| Question | Answer | Supporting quote | Justification |
|----------|--------|-----------------|---------------|
| 2.1 Were participants aware of assigned intervention? | Y | "We assigned men with metastatic, hormone-sensitive prostate cancer to receive either ADT plus docetaxel ... or ADT alone." (Methods) | Participants were explicitly informed of their treatment allocation because the interventions (chemotherapy vs hormone therapy alone) are distinct and no blinding procedure is described. |
| 2.2 Were carers and people delivering interventions aware? | Y | "We assigned men ... to receive either ADT plus docetaxel ... or ADT alone." (Methods) | Healthcare providers administering the interventions would necessarily know the allocation, as chemotherapy administration cannot be masked and no blinding of staff is reported. |
| 2.3 Were there trial-context deviations? | N | "6 patients in the combination group did not start the assigned therapy" (Results) | Deviations were limited to non‑initiation of therapy and are not described as arising from trial context. |
| 2.6 Was an appropriate ITT analysis used? | Y | "An intention-to-treat analysis was conducted that included all randomly assigned patients regardless of eligibility and treatment status." (Statistical Analysis) | All randomized participants were analyzed in their assigned groups, meeting ITT criteria. |

**Domain 2 judgment: Low**
**Algorithm rationale:** Part1=Low (Part1 Low: awareness present/unclear but no trial-context deviations); Part2=Low (2.6=Y/PY (appropriate ITT analysis) -> Part2=Low)

## Domain 3: Bias due to missing outcome data

| Question | Answer | Supporting quote | Justification |
|----------|--------|-----------------|---------------|
| 3.1 Were outcome data available for nearly all participants? | Y | "All randomly assigned patients were followed and included in the primary analysis of their assigned group." (Patients section) | Survival outcomes were reported for every randomized participant, with deaths enumerated and censored participants accounted for. |

**Domain 3 judgment: Low**
**Algorithm rationale:** 3.1=Y/PY (nearly complete data) -> Low

## Domain 4: Bias in measurement of the outcome

| Question | Answer | Supporting quote | Justification |
|----------|--------|-----------------|---------------|
| 4.1 Was the outcome measurement method inappropriate? | N | "Overall survival" (outcome_measurement) | All-cause mortality is an objective, standard outcome measured via vital status records. |
| 4.2 Could measurement have differed between groups? | N | "Patients were enrolled... All patients provided written informed consent" (blinding_section) | Death ascertainment procedures were applied identically to both arms. |
| 4.3 Were outcome assessors aware of intervention received? | N | "The ECOG-ACRIN Statistical Center collected the data" (blinding_section) | Outcome data were collected centrally and not dependent on knowledge of treatment allocation. |

**Domain 4 judgment: Low**
**Algorithm rationale:** 4.1=N/PN/NI, 4.2=N/PN, and 4.3=N/PN -> Low

## Domain 5: Bias in selection of the reported result

| Question | Answer | Supporting quote | Justification |
|----------|--------|-----------------|---------------|
| 5.1 Was analysis in accordance with a pre-specified plan? | PY | "With each amendment, the sample size was adjusted... an intention-to-treat analysis plan was used... Kaplan-Meier estimates... Cox proportional-hazard models, stratified according to the factors described above, were used to estimate hazard ratios... An intention-to-treat analysis was conducted that included all randomly assigned patients regardless of eligibility and treatment status" (Statistical Analysis Plan) | The protocol specifies an ITT, stratified Cox analysis before any outcome data were unblinded, but detailed timing of finalization is not explicit. |
| 5.2 Was result selected from multiple outcome measurements? | N | "Overall survival was the registered primary endpoint" (Registration/Protocol section) and the result reported is the hazard ratio for overall survival. | All eligible measurements for the primary outcome (overall survival) are reported; no alternative time points or definitions are presented. |
| 5.3 Was result selected from multiple analyses? | N | "Cox proportional-hazard models, stratified according to the factors described above, were used to estimate hazard ratios for time-to-event end points" (Statistical Analysis Plan) | Only the pre‑specified stratified Cox model is presented; no alternative adjusted or unadjusted analyses are reported. |

**Domain 5 judgment: Low**
**Algorithm rationale:** 5.1=Y/PY and 5.2=5.3=N/PN -> Low

## Overall risk of bias

**Overall judgment: Some concerns**

**Rationale:** Some concerns in 1 domain(s): D1

## Limitations of this assessment
This is an automated first-pass assessment for human review. Human verification is required, especially for 2 NI answer(s), high-uncertainty signaling questions (None), and any overall-judgment escalation flagged in the rationale.

## Quality flags
- NI answers: 2
- High-uncertainty signaling questions: None
- Human review priority: MEDIUM