# RoB 2 Signaling Question → Domain Judgment Algorithms

Source: "Revised Cochrane risk-of-bias tool for randomized trials (RoB 2)" guidance document, 22 August 2019, edited by Higgins, Savovic, Page, and Sterne.

Official download: https://drive.google.com/open?id=19R9savfPdCHC8XLz2iiMvL_71lPJERWK

Notation: Y/PY = "Yes" or "Probably yes"; N/PN = "No" or "Probably no"; NI = "No information"; NA = "Not applicable."

---

## Domain 1: Bias arising from the randomization process

**Signaling questions:**
- 1.1 Was the allocation sequence random?
- 1.2 Was the allocation sequence concealed until participants were enrolled and assigned to interventions?
- 1.3 Did baseline differences between intervention groups suggest a problem with the randomization process?

**Algorithm:**

| 1.1 Sequence random? | 1.2 Allocation concealed? | 1.3 Imbalance suggest problem? | Domain judgment |
|---|---|---|---|
| Y/PY/NI | Y/PY | NI/N/PN | **Low** |
| Y/PY | Y/PY | Y/PY | **Some concerns** |
| N/PN/NI | Y/PY | Y/PY | **Some concerns** |
| Any response | NI | N/PN/NI | **Some concerns** |
| Any response | NI | Y/PY | **High** |
| Any response | N/PN | Any response | **High** |

---

## Domain 2: Bias due to deviations from intended interventions

### Version A: Effect of assignment to intervention (ITT)

**Signaling questions:**
- 2.1 Were participants aware of their assigned intervention during the trial?
- 2.2 Were carers and people delivering the interventions aware of participants' assigned intervention?
- 2.3 If Y/PY/NI to 2.1 or 2.2: Were there deviations from the intended intervention that arose because of the trial context?
- 2.4 If Y/PY to 2.3: Were these deviations likely to have affected the outcome?
- 2.5 If Y/PY/NI to 2.4: Were these deviations from intended intervention balanced between groups?
- 2.6 Was an appropriate analysis used to estimate the effect of assignment to intervention?
- 2.7 If N/PN/NI to 2.6: Was there potential for a substantial impact (on the result) of the failure to analyse participants in the group to which they were randomized?

**Algorithm Part 1 (Qs 2.1-2.5):**

| 2.1 Participants aware? | 2.2 Personnel aware? | 2.3 Any deviations? | 2.4 Affecting outcomes? | 2.5 Balanced deviations? | Part 1 judgment |
|---|---|---|---|---|---|
| Both 2.1 & 2.2 N/PN | NA | NA | NA | NA | **Low** |
| Either Y/PY/NI | N/PN | NA | NA | NA | **Low** |
| Either Y/PY/NI | NI | NA | NA | NA | **Some concerns** |
| Either Y/PY/NI | Y/PY | N/PN | NA | NA | **Some concerns** |
| Either Y/PY/NI | Y/PY | Y/PY/NI | Y/PY | Y/PY | **Some concerns** |
| Either Y/PY/NI | Y/PY | Y/PY/NI | N/PN/NI | N/PN/NI | **High** |

**Algorithm Part 2 (Qs 2.6-2.7):**

| 2.6 Appropriate analysis? | 2.7 Substantial impact? | Part 2 judgment |
|---|---|---|
| Y/PY | NA | **Low** |
| N/PN/NI | N/PN | **Some concerns** |
| N/PN/NI | Y/PY/NI | **High** |

**Combining Parts 1 and 2:**
- Low in Part 1 AND Low in Part 2 = **Low**
- Some concerns in either, AND NOT High in either = **Some concerns**
- High in either Part 1 OR Part 2 = **High**

### Version B: Effect of adhering to intervention (per-protocol)

**Signaling questions:**
- 2.1 Were participants aware of their assigned intervention?
- 2.2 Were carers/people delivering interventions aware?
- 2.3 Were important non-protocol interventions balanced across intervention groups?
- 2.4 Were there failures in implementing the intervention that could have affected the outcome?
- 2.5 Was there non-adherence to the assigned intervention regimen that could have affected participants' outcomes?
- 2.6 Was an appropriate analysis used to estimate the effect of adhering to intervention?

**Algorithm:**

| 2.1 Participant aware? | 2.2 Personnel aware? | 2.3 Balanced non-protocol? | 2.4 Implementation failure? | 2.5 Non-adherence? | 2.6 Appropriate analysis? | Domain judgment |
|---|---|---|---|---|---|---|
| Both N/PN | Both N/PN | NA | N/PN or NA | N/PN or NA | NA | **Low** |
| Either Y/PY/NI | Either Y/PY/NI | Y/PY or NA | N/PN or NA | N/PN or NA | NA | **Low** |
| Both N/PN | Both N/PN | NA | Y/PY/NI | N/PN or NA | Y/PY | **Some concerns** |
| Both N/PN | Both N/PN | NA | N/PN or NA | Y/PY/NI | Y/PY | **Some concerns** |
| Either Y/PY/NI | Either Y/PY/NI | Y/PY or NA | Y/PY/NI | N/PN or NA | Y/PY | **Some concerns** |
| Either Y/PY/NI | Either Y/PY/NI | Y/PY or NA | N/PN or NA | Y/PY/NI | Y/PY | **Some concerns** |
| Either Y/PY/NI | Either Y/PY/NI | N/PN/NI | Any | Any | Y/PY | **Some concerns** |
| Both N/PN | Both N/PN | NA | Y/PY/NI | N/PN or NA | N/PN/NI | **High** |
| Both N/PN | Both N/PN | NA | N/PN or NA | Y/PY/NI | N/PN/NI | **High** |
| Either Y/PY/NI | Either Y/PY/NI | Y/PY or NA | Y/PY/NI | N/PN or NA | N/PN/NI | **High** |
| Either Y/PY/NI | Either Y/PY/NI | Y/PY or NA | N/PN or NA | Y/PY/NI | N/PN/NI | **High** |
| Either Y/PY/NI | Either Y/PY/NI | N/PN/NI | Any | Any | N/PN/NI | **High** |

---

## Domain 3: Bias due to missing outcome data

**Signaling questions:**
- 3.1 Were data for this outcome available for all, or nearly all, randomized participants?
- 3.2 If N/PN/NI to 3.1: Is there evidence that the result was not biased by missing outcome data?
- 3.3 If N/PN to 3.2: Could missingness in the outcome depend on its true value?
- 3.4 If Y/PY/NI to 3.3: Is it likely that missingness in the outcome depended on its true value?

Note: "Nearly all" for Q3.1 = >95% of randomized participants with outcome data (continuous outcomes). For dichotomous outcomes, also check whether missing data is negligible relative to observed events.

**Algorithm:**

| 3.1 Complete data? | 3.2 Evidence of no bias? | 3.3 Could depend on true? | 3.4 Likely depend on true? | Domain judgment |
|---|---|---|---|---|
| Y/PY | NA | NA | NA | **Low** |
| N/PN/NI | Y/PY | NA | NA | **Low** |
| N/PN/NI | N/PN | N/PN | NA | **Low** |
| N/PN/NI | N/PN | Y/PY/NI | N/PN | **Some concerns** |
| N/PN/NI | N/PN | Y/PY/NI | Y/PY/NI | **High** |

---

## Domain 4: Bias in measurement of the outcome

**Signaling questions:**
- 4.1 Was the method of measuring the outcome inappropriate?
- 4.2 Could measurement or ascertainment of the outcome have differed between intervention groups?
- 4.3 If N/PN/NI to 4.1 and 4.2: Were outcome assessors aware of the intervention received by study participants?
- 4.4 If Y/PY/NI to 4.3: Could assessment of the outcome have been influenced by knowledge of intervention received?
- 4.5 If Y/PY/NI to 4.4: Is it likely that assessment of the outcome was influenced by knowledge of intervention received?

**Algorithm:**

| 4.1 Inappropriate? | 4.2 Differed between groups? | 4.3 Aware? | 4.4 Could be influenced? | 4.5 Likely influenced? | Domain judgment |
|---|---|---|---|---|---|
| N/PN/NI | N/PN | N/PN | NA | NA | **Low** |
| N/PN/NI | N/PN | Y/PY/NI | N/PN | NA | **Low** |
| N/PN/NI | N/PN | Y/PY/NI | Y/PY/NI | N/PN | **Some concerns** |
| N/PN/NI | N/PN | Y/PY/NI | Y/PY/NI | Y/PY/NI | **High** |
| N/PN/NI | NI | N/PN | NA | NA | **Some concerns** |
| N/PN/NI | NI | Y/PY/NI | N/PN | NA | **Some concerns** |
| N/PN/NI | NI | Y/PY/NI | Y/PY/NI | N/PN | **Some concerns** |
| N/PN/NI | NI | Y/PY/NI | Y/PY/NI | Y/PY/NI | **High** |
| Y/PY | Any | Any | Any | Any | **High** |
| Any | Y/PY | Any | Any | Any | **High** |

---

## Domain 5: Bias in selection of the reported result

**Signaling questions:**
- 5.1 Were the data that produced this result analysed in accordance with a pre-specified analysis plan that was finalised before unblinded outcome data were available for analysis?
- 5.2 Is the numerical result being assessed likely to have been selected from multiple eligible outcome measurements (e.g. scales, definitions, time points) within the outcome domain?
- 5.3 Is the numerical result being assessed likely to have been selected from multiple eligible analyses of the data?

**Algorithm:**

| 5.1 In accordance with plan? | 5.2 Selected from multiple outcomes? | 5.3 Selected from multiple analyses? | Domain judgment |
|---|---|---|---|
| Y/PY | N/PN | N/PN | **Low** |
| N/PN/NI | N/PN | N/PN | **Some concerns** |
| Any | N/PN | NI | **Some concerns** |
| Any | NI | N/PN | **Some concerns** |
| Any | NI | NI | **Some concerns** |
| Any | Either 5.2 or 5.3 Y/PY | Either 5.2 or 5.3 Y/PY | **High** |

---

## Overall risk-of-bias judgment

| Overall judgment | Criteria |
|---|---|
| **Low risk of bias** | Low risk of bias for ALL domains |
| **Some concerns** | Some concerns in at least one domain, but not High risk in any domain |
| **High risk of bias** | High risk of bias in at least one domain OR some concerns for multiple domains in a way that substantially lowers confidence in the result |

Note: The "multiple some concerns → high" rule requires judgment — cannot be fully automated. The skill should flag these cases for human review rather than auto-deciding.
