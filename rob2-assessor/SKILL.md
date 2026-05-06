---
name: rob2-assessor
description: Assess risk of bias in randomized controlled trials using the Cochrane RoB 2 tool. Use this skill whenever someone asks to evaluate, assess, or check the risk of bias in an RCT, run a RoB 2 assessment, judge trial quality for a systematic review, or anything involving the Cochrane risk-of-bias tool for randomized trials. Also trigger when someone mentions "signaling questions," "bias domains," or wants to know if they can trust a trial's results for inclusion in a review.
---

# RoB 2 Assessor

Automate Cochrane Risk of Bias 2 (RoB 2) assessments for randomized controlled trials. Given a trial paper (PDF or text), produce a structured assessment with 22 signaling questions answered, each backed by a direct quote from the source document, domain-level judgments, and an overall risk-of-bias judgment.

## Why this matters

RoB 2 is the industry standard for judging whether an RCT's results can be trusted in a systematic review. It takes experienced reviewers 30-60 minutes per trial, per outcome. A systematic review with 30 trials means days of manual work. This skill produces a defensible first-pass draft that a human reviewer can audit in minutes instead of hours — because every answer comes with the exact quote from the paper that supports it.

## Source

This skill implements the official Cochrane RoB 2 tool:

> Sterne JAC, Savović J, Page MJ, et al. RoB 2: a revised tool for assessing risk of bias in randomised trials. *BMJ* 2019;366:l4898. doi: 10.1136/bmj.l4898

The signaling question → domain judgment decision tables in `references/rob2-algorithm.md` are reproduced from the companion guidance document (22 August 2019, Higgins, Savovic, Page, and Sterne), available at: https://drive.google.com/open?id=19R9savfPdCHC8XLz2iiMvL_71lPJERWK

## Before you start

### Verify the input is an RCT

Read the paper's methods section. Confirm that participants were **randomly assigned** to intervention vs. control/comparator groups. If the study is observational, a cohort study, a case-control study, or any non-randomized design, stop and tell the user: "This paper is not a randomized controlled trial. RoB 2 only applies to RCTs. For non-randomized studies, use ROBINS-I instead."

### Collect preliminary information

Before answering any signaling questions, establish the following (ask the user if not obvious from context):

1. **Experimental intervention** — what treatment/drug/procedure is being tested?
2. **Comparator intervention** — what is the control? (placebo, standard care, active comparator)
3. **Outcome being assessed** — which specific outcome? (RoB 2 is per-result, not per-trial. Different outcomes can have different risk-of-bias profiles. If the user doesn't specify, assess the primary outcome. If the trial has co-primary endpoints, ask the user which one to assess — OS and AE endpoints, for example, can differ substantially in their risk profile.)
4. **Numerical result** — the specific effect estimate being assessed (e.g., HR 0.64, 95% CI 0.54-0.77)
5. **Effect of interest** — default to **effect of assignment (intention-to-treat)**. Only use "effect of adhering to intervention (per-protocol)" if the user explicitly requests it. This choice changes the signaling questions in Domain 2.
6. **Sources consulted** — list what you read (main paper, protocol, supplementary materials, registry record if available)

Present these to the user before proceeding so they can correct anything.

## The assessment process

Read the full paper carefully before answering any questions. Pay particular attention to:
- Methods section (randomization, blinding, analysis approach)
- Results section (participant flow, missing data, outcomes reported)
- CONSORT flow diagram if present
- Supplementary materials if available
- Trial registration information if mentioned

Then work through each of the 5 domains below. For every signaling question:

1. **Answer** with one of: Y (Yes), PY (Probably Yes), PN (Probably No), N (No), NI (No Information)
2. **Quote** the specific text from the paper that supports your answer. Use the exact words from the paper in quotation marks, with a section reference (e.g., "Methods, Randomization" or "Results, p. 4").
3. **Justify** in one sentence why this quote leads to your answer.

The distinction between Y and PY (or N and PN): Y/N means firm evidence is stated in the text. PY/PN means you're making a reasonable inference from indirect evidence. For example, if a large trial run by an experienced clinical trials unit doesn't explicitly mention random sequence generation but everything else is rigorous, PY is more appropriate than NI.

NI ("No Information") is specifically reserved for cases where there genuinely isn't enough information to even make a "probably" judgment. It is not a default or a safe fallback — it should be used sparingly. If you can reasonably infer an answer from context, use PY or PN instead.

### Handling conditional questions

Some signaling questions are only asked if a previous question got a specific answer (e.g., "If Y/PY/NI to 2.1 or 2.2: ..."). When a conditional question doesn't apply because the triggering condition wasn't met, mark it as **NA** (Not Applicable) and move on. Do not answer it.

## The 5 domains

For every signaling question, the criteria below define when to select each answer option. Apply these before consulting `references/rob2-algorithm.md` for the domain judgment.

---

### Domain 1: Bias arising from the randomization process

**1.1** Was the allocation sequence random?

- **Y:** A recognized random method was explicitly described — e.g., computer-generated random numbers, random number tables, coin tossing, shuffling cards or envelopes, dice throwing, minimization, drawing lots — with no predictable or systematic element.
- **PY:** The study is a large, well-conducted trial in a reputable journal that lacks specific randomization details, but there are no indications of a non-random method.
- **PN:** Previous studies by the same research team have consistently used non-random methods, and the current study does not explicitly state a change in methodology.
- **N:** The sequence was non-random or predictable (e.g., alternation, date-based methods, patient ID numbers, clinician decisions, intervention availability), OR a random method is mentioned but combined with a predictable pattern.
- **NI:** The paper only states the study was "randomized" with no details about the randomization method.

**1.2** Was the allocation sequence concealed until participants were enrolled and assigned to interventions?

- **Y:** A remote or centrally controlled method was used (e.g., independent central pharmacy, telephone- or internet-based randomization service), OR sealed, opaque, sequentially numbered envelopes/containers were described and used correctly.
- **PY:** The report lacks detail but strongly implies adequate concealment (e.g., states "concealed allocation" without specifying the exact method).
- **PN:** The report lacks detail but suggests inadequate concealment (e.g., describes envelopes without stating they were sealed, opaque, and sequentially numbered).
- **N:** There is evidence that the enrolling investigator or participant could predict the allocation, OR the described method allows prediction of allocation.
- **NI:** The paper provides no information about allocation concealment, OR the information is too vague to assess adequacy.

**1.3** Did baseline differences between intervention groups suggest a problem with the randomization process?

Baseline differences that are compatible with chance do NOT indicate a problem. Only flag Y or PY if imbalances suggest the randomization failed or was subverted.

- **Y:** At least one of: major discrepancies in group sizes relative to the intended allocation ratio; an excess of statistically significant baseline differences beyond chance expectation; imbalances in key prognostic factors large enough to potentially bias effect estimates; improbably similar baseline characteristics between groups (suggesting possible data fabrication).
- **PY:** Some indications of potential issues with randomization, but not conclusive — e.g., slightly more statistically significant baseline differences than expected, but not an implausible excess.
- **PN:** Minor concerns about baseline differences, but they seem unlikely to significantly affect outcomes or introduce bias.
- **N:** No significant baseline imbalances, OR any observed differences are compatible with chance.
- **NI:** Baseline data are not provided, OR the information is inadequate to assess balance (e.g., abstract-only, or only analyzed participants' characteristics reported without raw baseline data).

---

### Domain 2: Bias due to deviations from intended interventions

**Effect of interest: assignment to intervention (ITT — the default)**

Important: An open-label trial is NOT automatically high risk. It depends on whether the lack of blinding led to deviations that actually affected the outcome. Many open-label trials are legitimately low risk, especially when the outcome is objective (e.g., death) and the analysis is intention-to-treat.

**2.1** Were participants aware of their assigned intervention during the trial?

- **Y:** Participants were explicitly informed of their group assignment; OR the intervention was impossible to blind (e.g., surgery vs. no surgery); OR all participants experienced obvious intervention-specific side effects.
- **PY:** The study design made it likely participants could guess their assignment; OR some participants may have experienced revealing side effects; OR blinding was attempted but likely ineffective.
- **PN:** Blinding methods were used but not explicitly verified; OR interventions were similar enough to make distinction difficult; OR no indication of compromised blinding is reported.
- **N:** The study explicitly states blinding was successful and verified; OR a robust, foolproof blinding method was used (e.g., identical placebos with matching appearance/taste/side-effect profiles).
- **NI:** The study does not mention blinding or participant awareness; OR insufficient detail is provided; OR blinding is mentioned with no information on its effectiveness.

**2.2** Were carers and people delivering the interventions aware of participants' assigned intervention during the trial?

- **Y:** The study explicitly states that carers/deliverers knew the assignments; OR the intervention nature made blinding impossible (e.g., surgery vs. medication); OR obvious side effects were visible to carers/deliverers.
- **PY:** Side effects likely revealed the intervention to some carers/deliverers; OR the allocation method was not properly concealed from care staff; OR the study design made it difficult to keep carers/deliverers unaware.
- **PN:** Blinding methods for carers/deliverers were described but not explicitly verified; OR interventions were similar enough to make distinction difficult; OR no indication of compromised blinding among carers/deliverers.
- **N:** The study explicitly confirms successful blinding of carers/deliverers; OR a robust blinding method was implemented and verified for this group.
- **NI:** The study does not mention blinding of carers/deliverers; OR insufficient detail is provided; OR blinding is mentioned with no information on its effectiveness for this group.

*If both 2.1 and 2.2 are N/PN → mark 2.3, 2.4, and 2.5 as NA and proceed to 2.6.*
*If either 2.1 or 2.2 is Y/PY/NI → answer 2.3.*

**2.3** [If Y/PY/NI to 2.1 or 2.2] Were there deviations from the intended intervention that arose because of the trial context?

- **Y:** Clear evidence that the trial context caused protocol deviations (e.g., documented cases of comparator-group participants seeking the experimental intervention because they felt "unlucky"; specific instances of trial personnel undermining protocol implementation).
- **PY:** Strong indications that trial context led to unauthorized interventions; OR reports that recruitment or engagement activities influenced adherence; OR evidence of blinding compromise leading to protocol-inconsistent changes.
- **PN:** Deviations appear typical of what would occur outside the trial; OR no indication that trial context influenced protocol adherence; OR changes in intervention seem solely due to standard clinical reasons.
- **N:** Deviations are explicitly stated to be unrelated to trial context; OR changes from assigned intervention are consistent with real-world scenarios; OR changes are protocol-consistent (e.g., dose reduction due to toxicity).
- **NI:** The study does not mention whether deviations arose from trial context; OR insufficient detail; OR deviations are reported but their relationship to trial context is unclear.

*If 2.3 is N/PN/NI/NA → mark 2.4 and 2.5 as NA and proceed to 2.6.*
*If 2.3 is Y/PY → answer 2.4.*

**2.4** [If Y/PY to 2.3] Were these deviations likely to have affected the outcome?

- **Y:** Clear evidence that deviations directly impacted the primary outcome; OR statistical analysis confirms a significant effect of deviations on results; OR large-scale protocol-inconsistent changes occurred that likely altered outcomes.
- **PY:** Deviations were substantial in areas likely to influence the outcome; OR patterns of trial context–induced non-adherence suggest potential impact; OR expert opinion or study authors indicate probable effect.
- **PN:** Deviations were minimal and unlikely to influence key outcomes; OR the nature of the changes suggests low probability of affecting results; OR the study design accounted for potential impact of minor deviations.
- **N:** Study explicitly states deviations did not affect the outcome; OR statistical analysis shows no significant impact; OR deviations were minor and unrelated to the primary outcome.
- **NI:** The study does not discuss the impact of deviations on outcomes; OR insufficient data; OR deviations are mentioned but their impact is not addressed.

*If 2.4 is N/PN/NA → mark 2.5 as NA and proceed to 2.6.*
*If 2.4 is Y/PY/NI → answer 2.5.*

**2.5** [If Y/PY/NI to 2.4] Were these deviations from intended intervention balanced between groups?

- **Y:** Clear evidence that deviations were equally distributed between groups; OR statistical analysis confirms no significant difference in deviation rates; OR study explicitly states deviations were balanced.
- **PY:** Data suggests similar patterns of deviations across groups; OR no notable differences in protocol adherence reported; OR authors indicate likely balanced without definitive proof.
- **PN:** Data suggests different patterns of deviations across groups; OR indications of higher non-adherence or protocol deviations in one group; OR authors suggest potential imbalance without definitive proof.
- **N:** Clear evidence of unequal distribution; OR statistical analysis shows significant imbalance in deviation rates; OR study explicitly states deviations were not balanced.
- **NI:** Study does not discuss the distribution of deviations between groups; OR insufficient data; OR deviations mentioned but their distribution across groups is not addressed.

**2.6** Was an appropriate analysis used to estimate the effect of assignment to intervention?

An appropriate analysis includes: (a) strict ITT (all randomized participants); (b) modified ITT (mITT) excluding only participants with missing outcome data; or (c) an analysis excluding only participants independently determined post-randomization to be ineligible. "As-treated" or naive per-protocol analyses (excluding non-adherent participants) are NOT appropriate for estimating the ITT effect.

- **Y:** Study used a clear ITT analysis; OR mITT excluding only those with missing data; OR post-randomization exclusions were limited to independently determined ineligible participants.
- **PY:** Analysis appears to follow ITT or appropriate mITT principles but lacks explicit confirmation; OR minimal post-randomization exclusions that likely don't impact results; OR authors indicate appropriate method without full details.
- **PN:** Analysis method suggests deviation from ITT principles; OR some inappropriate exclusions or regrouping of participants; OR authors hint at less appropriate methods.
- **N:** Naive per-protocol analysis was used (excluding non-adherent participants by choice); OR "as-treated" analysis was employed (grouping by received rather than assigned intervention); OR substantial post-randomization exclusions of eligible participants occurred.
- **NI:** Study does not specify the analysis method; OR insufficient detail; OR analysis is mentioned but its alignment with ITT principles is unclear.

*If 2.6 is Y/PY → mark 2.7 as NA.*
*If 2.6 is N/PN/NI → answer 2.7.*

**2.7** [If N/PN/NI to 2.6] Was there potential for a substantial impact (on the result) of the failure to analyse participants in the group to which they were randomised?

- **Y:** A large proportion of participants were analyzed in the wrong group or excluded; OR the outcome is rare and even small changes in analysis could substantially affect results; OR exclusions/misanalyses are strongly related to prognostic factors.
- **PY:** A moderate number of participants were analyzed incorrectly or excluded; OR there is reason to believe the misanalyses or exclusions could impact the results; OR the study design or outcome is sensitive to small changes in participant allocation.
- **PN:** Only a small number of participants were analyzed incorrectly or excluded; OR the outcome is common and the study design is robust to small analysis changes; OR misanalyses/exclusions appear unlikely to significantly affect results.
- **N:** Very few or no participants were analyzed in the wrong group or excluded; OR the outcome is common and robust to small changes in analysis; OR any misanalyses/exclusions are clearly unrelated to prognostic factors or outcomes.
- **NI:** Study does not provide information about participant analysis or exclusions; OR insufficient detail; OR the method of analysis is unclear or not reported.

**If the user requests effect of adhering to intervention (per-protocol)**, read the alternative Domain 2 signaling questions from `references/rob2-algorithm.md` (Version B section). Note: in non-inferiority trials, per-protocol analysis is often the primary pre-specified analysis — in those cases, Version B is the correct default, not an optional alternative.

---

### Domain 3: Bias due to missing outcome data

**3.1** Were data for this outcome available for all, or nearly all, participants randomised?

"Nearly all" generally means >95% of randomized participants have outcome data (continuous outcomes). For dichotomous outcomes, also check whether the number of missing participants is negligible relative to observed events — a small number of missing participants can still matter if the event rate is very low. Check the CONSORT flow diagram for exact numbers.

- **Y:** Data available for all randomized participants; OR for continuous outcomes: ≥95% of participants have data; OR for dichotomous outcomes: missing data is negligible compared to the number of observed events.
- **PY:** Data available for nearly all participants with minimal missing; OR number of missing outcomes unlikely to meaningfully affect results; OR authors indicate high completeness without exact figures.
- **PN:** Noticeable amount of missing data that may affect results; OR the proportion approaches or slightly exceeds acceptable thresholds; OR authors indicate concerns about missing data without providing exact figures.
- **N:** A significant proportion of outcome data is missing; OR the amount of missing data could substantially impact results; OR imputed data is used in place of actual outcome data.
- **NI:** Study provides no information about the extent of missing outcome data; OR unclear how many participants have complete data; OR completeness of outcome data is not addressed.

*If 3.1 is Y/PY → mark 3.2, 3.3, and 3.4 as NA.*
*If 3.1 is N/PN/NI → answer 3.2.*

**3.2** [If N/PN/NI to 3.1] Is there evidence that the result was not biased by missing outcome data?

Examples that support Y/PY: pre-specified sensitivity analyses (best-case/worst-case imputation, tipping-point analysis), multiple imputation accounting for the missing-at-random assumption, or a pattern-mixture model. LOCF (last-observation-carried-forward) imputation alone does NOT constitute adequate evidence.

- **Y:** Advanced analytical methods specifically designed to correct for missing data bias were used (e.g., multiple imputation, pattern-mixture models); AND comprehensive sensitivity analyses demonstrate stable results under various plausible assumptions; AND authors provide convincing evidence that missing data did not bias the results.
- **PY:** Appropriate methods were used to address missing data but with some limitations; OR sensitivity analyses suggest minimal impact; OR authors argue convincingly that missing data is unlikely to have biased results, but some uncertainty remains.
- **PN:** Methods used to address missing data are inadequate or poorly described; OR limited sensitivity analyses suggest potential for bias; OR authors acknowledge concerns about missing data without sufficient mitigation; OR minimal information about how missing data was handled.
- **N:** Simple imputation methods like LOCF were solely relied upon; OR no attempt was made to address potential bias from missing data; OR sensitivity analyses reveal substantial potential for bias; OR the study does not discuss how missing data was handled.

*If 3.2 is Y/PY → mark 3.3 and 3.4 as NA.*
*If 3.2 is N/PN → answer 3.3.*

**3.3** [If N/PN to 3.2] Could missingness in the outcome depend on its true value?

- **Y:** Clear evidence that loss to follow-up or withdrawal is related to participants' health status; OR missingness patterns strongly suggest a relationship with the true outcome value; OR in time-to-event analyses, substantial censoring that is likely related to the outcome.
- **PY:** Some indications that missingness might be related to the true outcome value; OR patterns of withdrawal suggest a possible link to health status; OR reasons for missing data are not fully documented or are ambiguous.
- **PN:** Most missing data has documented reasons unrelated to the outcome; OR patterns of missingness do not suggest a strong link to the true outcome value; OR authors provide plausible explanations for missingness unrelated to health status.
- **N:** All missing data is due to documented reasons clearly unrelated to the outcome (e.g., technical failures, relocation); OR strong evidence that loss to follow-up is not related to health status; OR in time-to-event analyses, censoring is minimal or clearly unrelated to the outcome.
- **NI:** Study provides no information about reasons for missing data; OR patterns of missingness are not described or analyzed; OR impossible to determine whether missingness could be related to the true outcome value.

*If 3.3 is N/PN → mark 3.4 as NA.*
*If 3.3 is Y/PY/NI → answer 3.4.*

**3.4** [If Y/PY/NI to 3.3] Is it likely that missingness in the outcome depended on its true value?

- **Y:** Clear differences in missing data proportions between intervention groups; OR reported reasons strongly suggest dependence on true outcome value; OR reasons for missing data significantly differ between groups; OR the trial context makes outcome-dependent missingness likely (e.g., participants with severe illness more likely to withdraw when not responding); OR in time-to-event analyses, censoring due to treatment changes is likely outcome-dependent.
- **PY:** Some differences in missing data proportions between groups; OR reasons hint at possible dependence on true outcome value; OR some variation in missing data reasons between groups; OR trial context suggests potential for outcome-dependent missingness; OR moderate censoring with possible outcome dependence.
- **PN:** Minor differences in missing data proportions between groups; OR reasons mostly unrelated to true outcome value; OR similar reasons for missing data across groups; OR trial context does not strongly suggest outcome-dependent missingness; OR limited censoring likely unrelated to outcome.
- **N:** No significant differences in missing data proportions between groups; OR reasons clearly unrelated to true outcome value; OR consistent reasons for missing data across groups; OR trial context suggests missingness is independent of outcome.
- **NI:** Study provides no information on missing data patterns or reasons; OR patterns are not described or analyzed; OR unable to determine whether missingness differs between intervention groups.

---

### Domain 4: Bias in measurement of the outcome

**4.1** Was the method of measuring the outcome inappropriate?

This question asks whether the *measurement method* was inappropriate for the outcome being measured — NOT whether the outcome itself (e.g., a surrogate endpoint) is an appropriate research choice. A surrogate endpoint measured with a valid, pre-specified method is not flagged here.

- **Y:** The measurement method is clearly insensitive to plausible intervention effects; OR the instrument used has been definitively shown to have poor validity; OR the method is entirely inappropriate for the outcome being measured.
- **PY:** There are strong indications that the method may not detect relevant changes; OR the instrument's validity is questionable based on available evidence; OR the method seems ill-suited for the outcome, but with some uncertainty.
- **PN:** The method appears suitable but there is limited information on its sensitivity; OR the instrument's validity is generally accepted but not rigorously proven; OR the method seems appropriate with minor concerns.
- **N:** The measurement method was specifically chosen or pre-specified for this outcome; OR the instrument has well-established validity; OR the method is clearly appropriate and sensitive to potential intervention effects.
- **NI:** The study provides no details about the method of outcome measurement; OR insufficient information to judge appropriateness; OR the measurement approach is mentioned but not described in enough detail.

**4.2** Could measurement or ascertainment of the outcome have differed between intervention groups?

- **Y:** Clear evidence of different outcome measurement methods or frequencies between groups; OR one group had substantially more healthcare visits, increasing outcome detection chances; OR explicit differences in data collection procedures that could introduce diagnostic detection bias.
- **PY:** Some indications of differences in measurement methods or timing between groups; OR slight variations in visit frequency that might affect outcome detection; OR potential for diagnostic detection bias, but not definitively confirmed.
- **PN:** Most aspects of measurement appear consistent across groups, with minor uncertainties; OR slight differences in timing or methods unlikely to significantly affect results; OR authors indicate efforts to maintain consistency, but some details are lacking.
- **N:** Clear evidence that identical measurement methods and thresholds were used for all groups; OR timing of measurements was consistent across groups; OR study design explicitly ensured uniform data collection procedures.
- **NI:** Study provides no details about measurement methods across groups; OR insufficient information to determine whether measurements differed; OR measurement procedures mentioned but not in enough detail to assess consistency.

*If 4.1 or 4.2 is Y/PY → mark 4.3, 4.4, and 4.5 as NA.*
*If both 4.1 and 4.2 are N/PN/NI → answer 4.3.*

**4.3** [If N/PN/NI to both 4.1 and 4.2] Were outcome assessors aware of the intervention received by study participants?

For patient-reported outcomes, the participant is the outcome assessor — so if participants knew their group assignment (as in an open-label trial), Q4.3 = Y by default.

- **Y:** Clear statement that outcome assessors were aware of intervention assignments; OR for patient-reported outcomes: participants were explicitly informed of (or could not avoid knowing) their intervention group; OR the study design made it impossible to blind outcome assessors.
- **PY:** Study suggests outcome assessors likely knew assignments but does not explicitly state it; OR for patient-reported outcomes: participants could likely deduce their group; OR blinding was attempted but likely ineffective.
- **PN:** Study mentions attempts to blind outcome assessors but does not confirm success; OR for patient-reported outcomes: efforts to keep participants unaware, but effectiveness is uncertain; OR design suggests assessor blinding was likely but not explicitly stated.
- **N:** Clear statement that outcome assessors were blinded to intervention assignments; OR for patient-reported outcomes: participants were definitively unaware of their group; OR robust blinding procedures were implemented and verified.
- **NI:** Study provides no information about assessor awareness; OR for patient-reported outcomes: participant knowledge of group assignment is not addressed; OR blinding of outcome assessment is not mentioned.

*If 4.3 is N/PN → mark 4.4 and 4.5 as NA.*
*If 4.3 is Y/PY/NI → answer 4.4.*

**4.4** [If Y/PY/NI to 4.3] Could assessment of the outcome have been influenced by knowledge of intervention received?

Objective outcomes (death, lab values, imaging-confirmed events) are much less susceptible to influence than subjective outcomes (patient-reported symptoms, clinician-judged response).

**AE endpoints:** For patient-reported AEs (nausea, fatigue, pain), Q4.4 is typically Y/PY — subjective self-report is directly shaped by expectation. For clinician-graded AEs (CTCAE), grading involves clinical judgment and Q4.4 is often Y/PY as well. Do not default to Low risk for AE domains in open-label trials without explicitly working through 4.3–4.5.

- **Y:** The outcome is clearly subjective and patient-reported (e.g., pain, nausea, quality of life); OR observer-reported outcomes involve significant judgment (e.g., clinician-graded symptom improvement); OR intervention providers make decisions that directly affect the outcome and know the treatment assignment.
- **PY:** The outcome has both subjective and objective elements and subjectivity could play a significant role; OR potential for bias in observer-reported outcomes, though efforts were made to standardize assessment; OR intervention providers' decisions might indirectly influence the outcome.
- **PN:** The outcome is mostly objective with minimal room for subjective interpretation; OR observer-reported outcomes involve limited judgment with clear, standardized assessment criteria; OR knowledge of intervention is unlikely to significantly influence the assessment process.
- **N:** The outcome is entirely objective (e.g., all-cause mortality, centrally adjudicated imaging); OR assessment criteria are rigidly defined and leave no room for subjective interpretation; OR the nature of the outcome precludes influence from knowledge of the intervention.
- **NI:** Study does not provide enough details about the nature of the outcome assessment; OR unclear whether the outcome involves subjective elements; OR the potential influence of intervention knowledge on assessment is not addressed.

*If 4.4 is N/PN → mark 4.5 as NA.*
*If 4.4 is Y/PY/NI → answer 4.5.*

**4.5** [If Y/PY/NI to 4.4] Is it likely that assessment of the outcome was influenced by knowledge of intervention received?

- **Y:** Strong beliefs about intervention benefits or harms are evident and likely influenced assessment; OR clear examples of bias in patient-reported outcomes due to expectations (e.g., trials with a heavily favored intervention where placebo recipients report amplified symptoms); OR outcome assessors were directly involved in delivering the intervention and likely biased in their evaluation.
- **PY:** Moderate beliefs about intervention effects might have influenced assessment; OR some indications of potential bias in subjective evaluations, but not definitively proven; OR outcome assessors had some involvement in intervention delivery.
- **PN:** Minimal beliefs about intervention effects that are unlikely to have significantly influenced assessment; OR slight potential for bias, but measures were taken to minimize it; OR outcome assessors had limited or no involvement in intervention delivery.
- **N:** No apparent beliefs about intervention effects that could have influenced assessment; OR objective measures were used, minimizing potential for bias even if intervention was known; OR clear separation between intervention delivery and outcome assessment.
- **NI:** Study does not provide enough information about beliefs or expectations regarding the intervention; OR unclear whether outcome assessors were involved in intervention delivery; OR the potential for assessment bias due to knowledge of intervention is not addressed.

---

### Domain 5: Bias in selection of the reported result

**5.1** Were the data that produced this result analysed in accordance with a pre-specified analysis plan that was finalised before unblinded outcome data were available for analysis?

If the trial registration number is reported, actively look up the registry record (ClinicalTrials.gov, ISRCTN.org) and compare the registered primary endpoint, sample size, and analysis plan against what was actually reported. A change in primary endpoint without explanation is a yellow flag.

- **Y:** A detailed analysis plan was finalized before any unblinded outcome data were available; AND the study explicitly states adherence to it; AND any changes to the plan were made before unblinding or for reasons clearly unrelated to the data.
- **PY:** Strong indication of a pre-specified plan, but some details are unclear; OR the analysis seems to follow standard practices that were likely pre-specified; OR minor deviations from the plan are explained and justified.
- **PN:** Some aspects of the analysis appear to have been decided after data were unblinded; OR the pre-specified plan is mentioned but not detailed enough to confirm full adherence; OR there are unexplained deviations from the apparent original plan.
- **N:** Clear evidence that major analysis decisions were made after unblinded data were available; OR the study explicitly states that the analysis plan was modified based on preliminary results; OR multiple analyses were conducted with selective reporting of favorable outcomes.
- **NI:** Study does not mention a pre-specified analysis plan; OR insufficient information to determine when the plan was finalized; OR unclear whether the analysis was planned before or after data unblinding.

**5.2** Is the numerical result being assessed likely to have been selected, on the basis of the results, from multiple eligible outcome measurements (e.g., scales, definitions, time points) within the outcome domain?

- **Y:** Multiple valid outcome measurements were clearly available; AND only a subset is reported without justification; AND there is clear evidence that result selection was based on favorability or statistical significance.
- **PY:** Multiple measurements were likely available, though not explicitly stated; OR reporting seems selective, with a bias towards favorable or significant results; OR the choice of reported outcomes is not fully justified and appears potentially biased.
- **PN:** Most intended measurements are reported, with minor omissions explained; OR the outcome domain has limited measurement options, reducing the possibility of selective reporting; OR any inconsistencies in reporting are reasonably justified.
- **N:** All intended measurements are consistently reported per the pre-specified analysis protocol; OR the outcome could only be measured in one way, eliminating selection possibility; OR any reporting inconsistencies are clearly explained by factors unrelated to results.
- **NI:** Study lacks details about analysis intentions or available measurements; OR unclear whether multiple eligible measurements were available; OR insufficient information to determine if result selection occurred.

**5.3** Is the numerical result being assessed likely to have been selected, on the basis of the results, from multiple eligible analyses of the data?

- **Y:** Multiple valid analytical approaches were clearly available; AND only a subset is reported without justification; AND there is clear evidence that analysis selection was based on favorability or statistical significance.
- **PY:** Multiple analytical methods were likely used, though not explicitly stated; OR reporting seems selective, with a bias towards favorable or significant results; OR the choice of reported analyses is not fully justified and appears potentially biased.
- **PN:** Most intended analyses are reported, with minor omissions explained; OR the outcome has limited analytical options, reducing selection possibility; OR any inconsistencies in reported analyses are reasonably justified.
- **N:** All intended analyses are consistently reported per the pre-specified analysis protocol; OR the outcome could only be analyzed in one way, eliminating selection possibility; OR any reporting inconsistencies are clearly explained by factors unrelated to results.
- **NI:** Study lacks details about analysis plans or available analytical methods; OR unclear whether multiple eligible analyses were conducted; OR insufficient information to determine if analysis selection occurred.

## Generating judgments

After answering all signaling questions for a domain, read `references/rob2-algorithm.md` and apply the decision table for that domain to determine the domain-level judgment (Low / Some concerns / High).

For the **overall judgment**, apply the rollup rule:
- **Low** = Low in ALL domains
- **Some concerns** = Some concerns in at least one domain, but not High in any
- **High** = High in at least one domain, OR some concerns in multiple domains in a way that substantially lowers confidence

The "multiple some concerns" clause is inherently a judgment call. If you encounter it, flag it explicitly: state that the individual domains each have "some concerns" and explain whether, taken together, they substantially lower confidence in the result. As a practical guide: if 3 or more domains carry Some concerns, the overall judgment is very likely High — present this as the probable verdict and ask the user to confirm. If 2 domains carry Some concerns, present both options (Some concerns vs. High) with your reasoning and let the user decide.

## Output format

Present the assessment as structured markdown. Use this exact template:

```
# RoB 2 Assessment

## Trial information
- **Trial:** [name/identifier]
- **Citation:** [authors, journal, year]
- **Experimental intervention:** [intervention]
- **Comparator:** [comparator]
- **Outcome assessed:** [outcome]
- **Numerical result:** [effect estimate with CI]
- **Effect of interest:** Effect of assignment to intervention (intention-to-treat)
- **Sources consulted:** [list]

## Domain 1: Bias arising from the randomization process

| Question | Answer | Supporting quote | Justification |
|----------|--------|-----------------|---------------|
| 1.1 Was the allocation sequence random? | [Y/PY/PN/N/NI] | "[exact quote]" (Methods, p. X) | [one sentence] |
| 1.2 Was the allocation sequence concealed? | [answer] | "[quote]" (section) | [justification] |
| 1.3 Did baseline differences suggest a problem? | [answer] | "[quote]" (section) | [justification] |

**Domain 1 judgment: [Low / Some concerns / High]**
**Algorithm rationale:** [one sentence explaining which row of the decision table was matched]

[Repeat for Domains 2-5]

## Overall risk of bias

**Overall judgment: [Low / Some concerns / High]**

**Rationale:** [2-3 sentences summarizing why, referencing the domain judgments]

## Limitations of this assessment
[Note any areas where information was lacking, where the assessment required significant inference, or where a human reviewer should pay particular attention]
```

## Important principles

**Quote faithfulness is everything.** Every quote must be the actual text from the paper, not a paraphrase. If you cannot find text that directly addresses a signaling question, answer NI and state "No relevant text found in the available sources." A fabricated or paraphrased quote destroys the entire value of the assessment because the human reviewer can't verify it.

**This is a draft, not a verdict.** Frame the output as a first-pass assessment for human review. The skill reduces the reviewer's job from "do the whole assessment from scratch" to "check each answer against the quoted evidence and override where needed." Never claim the assessment is definitive.

**Err toward NI over fabrication.** If you're uncertain whether a piece of text actually supports an answer, it's better to say NI and let the human find the right quote than to stretch a quote to fit an answer it doesn't support. The reviewer will catch a genuine NI quickly; a plausible-but-wrong quote wastes their time.

**Respect the branching logic.** If a conditional question's trigger condition isn't met, mark it NA. Do not answer questions that the algorithm says to skip — answering them anyway confuses the decision table lookup.
