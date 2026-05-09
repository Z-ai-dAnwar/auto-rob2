# RoB 2 Assessment

## Trial information
- **Trial:** Abiraterone (1000 mg orally once daily) plus prednisone (5 mg orally twice daily) added to standard of care vs Standard of care (androgen deprivation therapy alone or with intravenous docetaxel 75 mg/m² every 3 weeks)
- **Citation:** Not reported
- **Experimental intervention:** Abiraterone (1000 mg orally once daily) plus prednisone (5 mg orally twice daily) added to standard of care
- **Comparator:** Standard of care (androgen deprivation therapy alone or with intravenous docetaxel 75 mg/m² every 3 weeks)
- **Outcome assessed:** Progression-Free Survival
- **Numerical result:** HR 0.54 (99.9% CI 0.41–0.71)
- **Effect of interest:** Effect of assignment to intervention (intention-to-treat)
- **Sources consulted:** methods, randomization, blinding, outcomes, analysis, results, missing_data, registration, baseline, consort, supplementary

## Domain 1: Bias arising from the randomization process

| Question | Answer | Supporting quote | Justification |
|----------|--------|-----------------|---------------|
| 1.1 Was the allocation sequence random? | Y | "Randomisation was done using a minimisation algorithm, stratified by study site, ECOG performance status..., with 80% probability to minimise imbalance in the number of patients assigned to each treatment group." (Randomisation_section) | The description of a computer‑based minimisation algorithm constitutes a recognized random method. |
| 1.2 Was the allocation sequence concealed? | Y | "Eligible patients were centrally randomly assigned in the Alea Clinical Portal..., performed via the Tenalea autonomous software, solely accessed by the trial data manager..." (Randomisation_section) | Centralised, software‑driven allocation performed by an independent data manager ensures concealment until enrolment. |
| 1.3 Did baseline differences suggest a problem? | N | "Table 1: Baseline characteristics in the intention-to-treat population" (Baseline_characteristics) – the presented numbers show comparable group sizes and balanced baseline variables. | Baseline characteristics are broadly similar across arms, indicating no evidence of a problem with randomisation. |

**Domain 1 judgment: Low**
**Algorithm rationale:** Row: Y-PY-NI / Y-PY / NI-N-PN -> Low

## Domain 2: Bias due to deviations from intended interventions

| Question | Answer | Supporting quote | Justification |
|----------|--------|-----------------|---------------|
| 2.1 Were participants aware of assigned intervention? | Y | "We conducted an open-label, randomised, activecontrolled, phase 3 study…" (Methods) | The trial is explicitly described as open‑label, indicating participants knew their assigned treatment. |
| 2.2 Were carers and people delivering interventions aware? | Y | "We conducted an open-label, randomised, activecontrolled, phase 3 study…" (Methods) | Because the study is open‑label, healthcare providers and trial personnel delivering the interventions were also aware of group allocation. |
| 2.3 Were there trial-context deviations? | N | "No relevant text found" | No trial-context-driven crossovers or contamination are reported. |
| 2.6 Was an appropriate ITT analysis used? | Y | "All efficacy analyses were conducted in the intention-to-treat population, defined as all patients who were randomly assigned to a treatment group." (Statistical analysis) | The study explicitly states that the primary effect was estimated using an ITT analysis, which is appropriate for assessing the effect of assignment. |

**Domain 2 judgment: Low**
**Algorithm rationale:** Part1=Low (Part1 Low condition met); Part2=Low (2.6=Y/PY (appropriate ITT analysis) -> Part2=Low)

## Domain 3: Bias due to missing outcome data

| Question | Answer | Supporting quote | Justification |
|----------|--------|-----------------|---------------|
| 3.1 Were outcome data available for nearly all participants? | Y | "Missing data ... 9 (2%) ... 15 (3%) ... 6 (2%) ... 8 (2%)" | Less than 5% of randomized participants lacked outcome data, meeting the >95% threshold for “nearly all”. |

**Domain 3 judgment: Low**
**Algorithm rationale:** 3.1=Y/PY (nearly complete data) -> Low

## Domain 4: Bias in measurement of the outcome

| Question | Answer | Supporting quote | Justification |
|----------|--------|-----------------|---------------|
| 4.1 Was the outcome measurement method inappropriate? | N | "radiographic progression‑free survival" (outcome_measurement) | Standard RECIST imaging is a validated, objective method. |
| 4.2 Could measurement have differed between groups? | N | "open‑label, randomised" (blinding_section) – no indication of different imaging schedules. | Both arms used the same imaging protocol. |
| 4.3 Were outcome assessors aware of intervention received? | Y | "open‑label" (blinding_section) | Assessors were not blinded to treatment allocation. |
| 4.4 Could knowledge of intervention influence assessment? | Y | "radiographic progression‑free survival" (outcome_measurement) | Interpretation of imaging can involve judgment, so knowledge could influence assessment. |
| 4.5 Was assessment likely influenced by knowledge? | N | "pre‑defined criteria" (RECIST) used for progression assessment | Standardised RECIST criteria limit subjective influence despite open‑label design. |

**Domain 4 judgment: Some concerns**
**Algorithm rationale:** Unresolved D4 answers: 4.1=N 4.2=N 4.3=Y 4.4=Y 4.5=N

## Domain 5: Bias in selection of the reported result

| Question | Answer | Supporting quote | Justification |
|----------|--------|-----------------|---------------|
| 5.1 Was analysis in accordance with a pre-specified plan? | Y | "The coprimary endpoints were radiographic progression-free survival and overall survival." (Methods section) | The outcome (progression-free survival) was pre‑specified as a co‑primary endpoint in the trial protocol. |
| 5.2 Was result selected from multiple outcome measurements? | N | "Adjusted Cox regression modelling revealed no interaction between abiraterone and radiotherapy, enabling the pooled analysis of abiraterone efficacy." (Results section) | Only a single, pre‑specified definition of radiographic progression‑free survival was used; no alternative measurements were presented. |
| 5.3 Was result selected from multiple analyses? | N | "All efficacy analyses were conducted in the intention‑to‑treat population... The Cox proportional hazards model adjusted for radiotherapy and stratification factors provided significances and an estimate of the abiraterone effect." (Statistical analysis plan) | The analysis follows the pre‑specified statistical analysis plan with no evidence of post‑hoc selective analytic choices. |

**Domain 5 judgment: Low**
**Algorithm rationale:** 5.1=Y/PY and 5.2=5.3=N/PN -> Low

## Overall risk of bias

**Overall judgment: Some concerns**

**Rationale:** Some concerns in 1 domain(s): D4

## Quality flags
- NI answers: 0
- High-uncertainty signaling questions: None
- Human review priority: MEDIUM

## Limitations of this assessment
This is an automated draft assessment. Human verification is required, especially for 0 NI answer(s) and high-uncertainty SQs: None.