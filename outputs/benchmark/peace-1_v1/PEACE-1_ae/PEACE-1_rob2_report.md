# RoB 2 Assessment

## Trial information
- **Trial:** abiraterone (1000 mg daily) plus prednisone (5 mg twice daily) added to standard of care (ADT alone or with docetaxel) vs standard of care (androgen deprivation therapy alone or with intravenous docetaxel 75 mg/m² every 3 weeks)
- **Citation:** Not reported
- **Experimental intervention:** abiraterone (1000 mg daily) plus prednisone (5 mg twice daily) added to standard of care (ADT alone or with docetaxel)
- **Comparator:** standard of care (androgen deprivation therapy alone or with intravenous docetaxel 75 mg/m² every 3 weeks)
- **Outcome assessed:** Adverse Events
- **Numerical result:** HR 0.54 (99.9% CI 0.41–0.71)
- **Effect of interest:** Effect of assignment to intervention (intention-to-treat)
- **Sources consulted:** methods, randomization, blinding, outcomes, analysis, results, missing_data, registration, baseline, consort, supplementary

## Domain 1: Bias arising from the randomization process

| Question | Answer | Supporting quote | Justification |
|----------|--------|-----------------|---------------|
| 1.1 Was the allocation sequence random? | Y | "Randomisation was done using a minimisation algorithm, stratified by study site, ECOG performance status..., with 80% probability to minimise imbalance in the number of patients assigned to each treatment group." (Randomisation_section) | The description of a computer‑based minimisation algorithm indicates a recognized random method was used. |
| 1.2 Was the allocation sequence concealed? | Y | "Eligible patients were centrally randomly assigned in the Alea Clinical Portal..., this randomisation process was performed via the Tenalea autonomous software, solely accessed by the trial data manager..." (Randomisation_section) | Centralised, web‑based allocation managed by an independent data manager ensures the sequence was concealed from enrolling clinicians. |
| 1.3 Did baseline differences suggest a problem? | N | "Table 1: Baseline characteristics in the intention-to-treat population" (Baseline_characteristics) | The baseline table shows comparable group sizes and characteristics, with no implausible imbalances suggesting a failure of randomisation. |

**Domain 1 judgment: Low**
**Algorithm rationale:** Row: Y-PY-NI / Y-PY / NI-N-PN -> Low

## Domain 2: Bias due to deviations from intended interventions

| Question | Answer | Supporting quote | Justification |
|----------|--------|-----------------|---------------|
| 2.1 Were participants aware of assigned intervention? | Y | "We conducted an open-label, randomised, activecontrolled, phase 3 study…" (Methods) | The trial is described as open‑label, indicating participants knew their assigned treatment. |
| 2.2 Were carers and people delivering interventions aware? | Y | "We conducted an open-label, randomised, activecontrolled, phase 3 study…" (Methods) | Because the study is open‑label, the healthcare providers and trial personnel delivering the interventions were also aware of group allocation. |
| 2.3 Were there trial-context deviations? | N | No relevant text found | No trial-context-driven crossovers or contamination are reported in the provided excerpts. |
| 2.6 Was an appropriate ITT analysis used? | N | "Safety analyses were conducted in the safety population, according to the treatment actually received by the patients (those who did not receive any investigational treatment were not included in the safety analyses)." (Results/Methods) | The analysis of adverse events used a per‑treated (as‑treated) safety population rather than an intention‑to‑treat approach. |
| 2.7 Was there potential for substantial impact? | Y | "Safety analyses were conducted in the safety population, according to the treatment actually received by the patients (those who did not receive any investigational treatment were not included in the safety analyses)." (Results/Methods) | Excluding participants who did not receive the investigational treatment could substantially affect the adverse‑event estimates, especially if exclusions are related to prognosis or tolerability. |

**Domain 2 judgment: High**
**Algorithm rationale:** Part1=Low (Part1 Low condition met); Part2=High (2.6=N/PN and 2.7=Y/PY -> Part2=High)

## Domain 3: Bias due to missing outcome data

| Question | Answer | Supporting quote | Justification |
|----------|--------|-----------------|---------------|
| 3.1 Were outcome data available for nearly all participants? | Y | "Missing data 9 (2%) ... 15 (3%) ... 6 (2%) ... 8 (2%)" (CONSORT flow) | Outcome data were available for >95% of participants, indicating near‑complete follow‑up. |

**Domain 3 judgment: Low**
**Algorithm rationale:** 3.1=Y/PY (nearly complete data) -> Low

## Domain 4: Bias in measurement of the outcome

| Question | Answer | Supporting quote | Justification |
|----------|--------|-----------------|---------------|
| 4.1 Was the outcome measurement method inappropriate? | N | "adverse events (mostly hypertension and aminotransferase increase)" (Added value of this study) | Standard clinician‑reported adverse event grading (e.g., CTCAE) is a validated method. |
| 4.2 Could measurement have differed between groups? | N | "open‑label, randomised, active‑controlled" (Methods) | Both arms were assessed with the same clinical procedures; no differential measurement described. |
| 4.3 Were outcome assessors aware of intervention received? | Y | "open‑label, randomised, active‑controlled" (Methods) | Outcome assessors (clinicians) were aware of the treatment allocation. |
| 4.4 Could knowledge of intervention influence assessment? | Y | "adverse events (mostly hypertension and aminotransferase increase)" (Added value of this study) | Clinician‑assessed adverse events require judgment and can be influenced by knowledge of treatment. |
| 4.5 Was assessment likely influenced by knowledge? | N | "adverse events (mostly hypertension and aminotransferase increase)" (Added value of this study) | Standardized CTCAE grading limits subjective bias; no evidence of differential application. |

**Domain 4 judgment: Some concerns**
**Algorithm rationale:** Unresolved D4 answers: 4.1=N 4.2=N 4.3=Y 4.4=Y 4.5=N

## Domain 5: Bias in selection of the reported result

| Question | Answer | Supporting quote | Justification |
|----------|--------|-----------------|---------------|
| 5.1 Was analysis in accordance with a pre-specified plan? | N | "grade 3 or worse adverse events occurred in 217 (63%) of 347 patients who received abiraterone and 181 (52%) of 350 who did not" (Results section) | Adverse events were not listed among the registered primary endpoints and no pre‑specified analysis plan for this safety outcome is provided, indicating the analysis was not pre‑specified. |
| 5.2 Was result selected from multiple outcome measurements? | N | "grade 3 or worse adverse events occurred in 217 (63%) of 347 patients who received abiraterone and 181 (52%) of 350 who did not" (Results section) | The report presents a single definition (grade ≥ 3) and time frame for adverse events, with no indication that alternative measurements were available or selectively omitted. |
| 5.3 Was result selected from multiple analyses? | N | "All efficacy analyses were conducted in the intention‑to‑treat population... Safety analyses were conducted in the safety population, according to the treatment actually received by the patients" (Statistical analysis plan) | The analysis follows the described safety‑population approach; no alternative analytic strategies are mentioned, suggesting no selective analysis of multiple options. |

**Domain 5 judgment: Some concerns**
**Algorithm rationale:** 5.1=N 5.2=N 5.3=N -> Some concerns

## Overall risk of bias

**Overall judgment: High**

**Rationale:** High in: D2

## Quality flags
- NI answers: 0
- High-uncertainty signaling questions: None
- Human review priority: HIGH

## Limitations of this assessment
This is an automated draft assessment. Human verification is required, especially for 0 NI answer(s) and high-uncertainty SQs: None.