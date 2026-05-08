PROMPT_RCT_SCREEN = """You are a systematic review methodologist. Your task is to determine whether this study is a randomized controlled trial (RCT).

Read the following text carefully:

<methods_section>
{methods_text}
</methods_section>

An RCT is a study in which participants were RANDOMLY assigned (by any random process: computer-generated numbers, random number tables, coin toss, minimization, drawing lots, etc.) to intervention vs. control/comparator groups.

Studies that are NOT RCTs: cohort studies, case-control studies, quasi-randomized trials (allocation by alternation, date of birth, record number, clinician judgment), and non-randomized experimental designs.

Respond in this exact XML format:

<screening>
  <is_rct>YES or NO</is_rct>
  <evidence>"[exact quote from text supporting your decision]"</evidence>
  <study_design>[brief description of the study design as reported]</study_design>
  <note>[if NO: state that ROBINS-I should be used instead; if YES: leave blank]</note>
</screening>"""

PROMPT_PRELIMINARY_INFO = """You are an expert systematic reviewer applying the Cochrane Risk of Bias 2 (RoB 2) tool. Before answering any signaling questions, extract key preliminary information about the trial.

Read these sections of the trial report:

<abstract>
{abstract_text}
</abstract>

<methods>
{methods_text}
</methods>

<results>
{results_text}
</results>

<registration>
{registration_text}
</registration>

<consort_flow>
{consort_text}
</consort_flow>

For each item below, provide: (1) the extracted value, and (2) the EXACT quoted text from the paper in quotation marks with a section reference. Do not paraphrase quotes.

<preliminary_info>
  <experimental_intervention>
    <value>[name and description of the treatment being tested]</value>
    <quote>"[exact text]" ([Section])</quote>
  </experimental_intervention>

  <comparator_intervention>
    <value>[name and description of the control arm]</value>
    <quote>"[exact text]" ([Section])</quote>
  </comparator_intervention>

  <outcome_assessed>
    <value>[specific outcome — use the PRIMARY outcome if user did not specify another]</value>
    <quote>"[exact text]" ([Section])</quote>
    <is_primary>YES or NO or UNCLEAR</is_primary>
  </outcome_assessed>

  <outcome_type>Classify the outcome type using exactly one of these five values:
  - vital-status: outcome is all-cause mortality or event defined purely as death with no
    clinical judgment required (e.g., "overall survival: time from randomisation to death
    from any cause")
  - biomarker: outcome is a laboratory or imaging measurement with a pre-defined numerical
    threshold (e.g., PSA < 0.2 ng/mL, complete metabolic response by PET criteria)
  - clinician-composite: composite time-to-event outcome requiring clinical or radiological
    judgment (e.g., progression-free survival, time to progression, disease-free survival
    where progression requires imaging interpretation or clinical assessment by RECIST or similar)
  - clinician-graded: outcome assessed using a standardised grading scale that still requires
    clinical judgment (e.g., adverse events by CTCAE, performance status by ECOG,
    investigator-assessed tumour response)
  - patient-reported: outcome assessed by the participant themselves via questionnaire
    (e.g., pain VAS, FACT-P, EQ-5D, HRQoL instruments)
</outcome_type>

  <numerical_result>
    <value>[effect estimate with CI, e.g., HR 0.64 (95% CI 0.54–0.77)]</value>
    <quote>"[exact text]" ([Section])</quote>
  </numerical_result>

  <n_randomized>
    <value>[total number randomized, as integer string]</value>
    <quote>"[exact text]" ([Section])</quote>
  </n_randomized>

  <trial_registration>
    <number>[registration number or "Not reported"]</number>
    <registry>[ClinicalTrials.gov or ISRCTN or "Not reported"]</registry>
    <quote>"[exact text]" or "Not reported"</quote>
  </trial_registration>

  <registered_primary_endpoint>
    <value>[primary endpoint listed in trial registry or protocol]</value>
    <quote>"[exact text]" ([Section])</quote>
  </registered_primary_endpoint>

  <registered_secondary_endpoints>List any secondary or co-primary endpoints from the trial
registration or protocol, exactly as stated. Separate multiple endpoints with semicolons.
If none found, write "Not reported".</registered_secondary_endpoints>

  <registered_analysis>
    <value>[pre-specified analysis approach from registry/protocol, e.g., ITT or per-protocol]</value>
    <quote>"[exact text]" ([Section])</quote>
  </registered_analysis>
</preliminary_info>

RULES:
- Every quote must be the EXACT words from the paper. Never paraphrase.
- If genuinely absent, write "Not reported" for value and "No relevant text found" for quote.
- Do not guess numerical results."""

PROMPT_DOMAIN1 = """You are an expert systematic reviewer applying the Cochrane Risk of Bias 2 (RoB 2) tool.

TRIAL: {intervention} vs {comparator} | Outcome: {outcome}

Read the following sections:

<randomization_section>
{randomization_text}
</randomization_section>

<baseline_characteristics>
{baseline_text}
</baseline_characteristics>

<consort_flow>
{consort_text}
</consort_flow>

---

Answer the three signaling questions for Domain 1: Bias arising from the randomization process.

For each question, choose exactly one answer: Y (Yes), PY (Probably Yes), PN (Probably No), N (No), or NI (No Information).

GENERAL RULES FOR ALL ANSWERS:
- Y/N = firm evidence is explicitly stated in the text
- PY/PN = reasonable inference from indirect evidence (use when context supports a judgment but wording is not explicit)
- NI = ONLY when you genuinely cannot make a "probably" judgment. NI is NOT a safe default. A large trial in a major journal that does not describe its randomization method should receive PY (not NI), because the context makes an adequate method probable.

---

QUESTION 1.1: Was the allocation sequence random?

Answer Y/PY if: a recognized random method is described (computer-generated numbers, random number tables, coin toss, minimization, drawing lots, shuffling cards/envelopes) — or it is a large, well-conducted trial with no indication of non-random methods.
Answer N/PN if: sequence was non-random or predictable (alternation, date-based, patient ID, clinician decision, availability) — or a random method is mentioned alongside a predictable pattern.
Answer NI ONLY if: the paper states only "randomized" with no details and no contextual clues.

QUESTION 1.2: Was the allocation sequence concealed until participants were enrolled and assigned?

Answer Y/PY if: remote/central randomization (telephone, internet, independent pharmacy) — or correctly described sealed opaque sequentially numbered envelopes/containers — or the report states "concealed allocation."
Answer N/PN if: the method allows prediction of next allocation (open lists, transparent envelopes, non-sequential).
Answer NI if: concealment is entirely absent from the report with no contextual clues.

QUESTION 1.3: Did baseline differences between intervention groups suggest a PROBLEM with the randomization process?

IMPORTANT: Baseline differences compatible with chance do NOT indicate a problem. Only answer Y/PY if there is evidence the randomization FAILED or was SUBVERTED.
Answer Y/PY ONLY if: major group-size discrepancies beyond the intended ratio — or an implausible excess of statistically significant baseline differences — or suspiciously identical baseline characteristics suggesting possible fabrication.
Answer N/PN if: differences are minor and compatible with chance (this is the most common correct answer when a baseline table is provided).
Answer NI if: no baseline data are provided.

---

<domain1>
  <sq_1_1>
    <answer>[Y/PY/PN/N/NI]</answer>
    <quote>"[exact text from paper]" ([Section reference])</quote>
    <justification>[one sentence explaining why this quote supports this answer]</justification>
  </sq_1_1>

  <sq_1_2>
    <answer>[Y/PY/PN/N/NI]</answer>
    <quote>"[exact text from paper]" ([Section reference])</quote>
    <justification>[one sentence]</justification>
  </sq_1_2>

  <sq_1_3>
    <answer>[Y/PY/PN/N/NI]</answer>
    <quote>"[exact text from paper]" ([Section reference])</quote>
    <justification>[one sentence]</justification>
  </sq_1_3>
</domain1>"""

PROMPT_DOMAIN2_SQ12 = """You are an expert systematic reviewer applying the Cochrane Risk of Bias 2 (RoB 2) tool.

TRIAL: {intervention} vs {comparator} | Outcome: {outcome} | Effect of interest: Intention-to-treat (ITT)

Read the following:

<blinding_section>
{blinding_text}
</blinding_section>

<methods_interventions>
{methods_text}
</methods_interventions>

---

Answer the first two signaling questions for Domain 2: Bias due to deviations from intended interventions.

CRITICAL REMINDER: An open-label trial is NOT automatically high risk. Risk depends on whether lack of blinding caused deviations that affected the outcome.

QUESTION 2.1: Were PARTICIPANTS aware of their assigned intervention during the trial?

Answer Y/PY if: explicitly informed of group assignment — or impossible to blind (e.g., surgery vs. no surgery) — or obvious intervention-specific side effects would reveal assignment.
Answer N/PN if: robust blinding was implemented with matched placebos; blinding was verified.
Answer NI if: blinding is not mentioned and the design does not make awareness obvious.

QUESTION 2.2: Were CARERS AND PEOPLE DELIVERING THE INTERVENTIONS aware of participants' assigned intervention?

Apply the same logic as Q2.1 but for healthcare providers and trial personnel. Note: In trials where delivery personnel cannot be blinded (e.g., surgical vs. medical treatment), answer Y. This does not automatically make the domain High risk — further questions will determine that.

---

<domain2_part1>
  <sq_2_1>
    <answer>[Y/PY/PN/N/NI]</answer>
    <quote>"[exact text]" ([Section])</quote>
    <justification>[one sentence]</justification>
  </sq_2_1>

  <sq_2_2>
    <answer>[Y/PY/PN/N/NI]</answer>
    <quote>"[exact text]" ([Section])</quote>
    <justification>[one sentence]</justification>
  </sq_2_2>
</domain2_part1>"""

PROMPT_DOMAIN2_CONDITIONAL = """You are an expert systematic reviewer applying the Cochrane Risk of Bias 2 (RoB 2) tool.

TRIAL: {intervention} vs {comparator} | Outcome: {outcome}
Prior answers: Q2.1 = {sq_2_1} | Q2.2 = {sq_2_2}

Read the following:

<protocol_adherence>
{deviations_text}
</protocol_adherence>

<concomitant_medications>
{concomitant_text}
</concomitant_medications>

---

Because participants and/or carers were aware of assigned intervention (Q2.1 or Q2.2 = Y/PY/NI), answer the following conditional questions.

QUESTION 2.3: Were there deviations from the intended intervention that AROSE BECAUSE OF THE TRIAL CONTEXT?

This asks specifically about deviations CAUSED by the trial itself (e.g., control-arm participants seeking experimental treatment because they felt unlucky; trial personnel undermining protocol due to awareness of assignments). It does NOT include protocol-consistent changes (e.g., dose reduction due to toxicity — these are expected and do not cause bias for the ITT effect).

Answer Y/PY if: documented trial-context-driven crossovers or contamination.
Answer N/PN if: deviations are protocol-consistent or would occur in normal clinical practice.
Answer NI if: deviations reported but their relationship to trial context is unclear.

IF 2.3 = N/PN/NI: set 2.4 and 2.5 to NA.
IF 2.3 = Y/PY: answer Q2.4.

QUESTION 2.4 [only if 2.3 = Y/PY]: Were these deviations LIKELY TO HAVE AFFECTED THE OUTCOME?

Answer Y/PY if: deviations were substantial and biologically plausible to affect this specific outcome.
Answer N/PN if: deviations were minor or the outcome is objective and unlikely to be affected.
Answer NI if: impossible to judge from available information.

IF 2.4 = N/PN/NA: set 2.5 to NA.
IF 2.4 = Y/PY/NI: answer Q2.5.

QUESTION 2.5 [only if 2.4 = Y/PY/NI]: Were these deviations BALANCED BETWEEN GROUPS?

Answer Y/PY if: similar deviation rates in both arms.
Answer N/PN if: one arm had substantially more deviations.

---

<domain2_conditional>
  <sq_2_3>
    <answer>[Y/PY/PN/N/NI]</answer>
    <quote>"[exact text]" ([Section]) or "No relevant text found"</quote>
    <justification>[one sentence]</justification>
  </sq_2_3>

  <sq_2_4>
    <answer>[Y/PY/PN/N/NI or NA]</answer>
    <quote>"[exact text]" or "Not applicable"</quote>
    <justification>[one sentence or "Not applicable"]</justification>
    <uncertainty_flag>[HIGH if subjective judgment with limited evidence, otherwise NORMAL]</uncertainty_flag>
  </sq_2_4>

  <sq_2_5>
    <answer>[Y/PY/PN/N/NI or NA]</answer>
    <quote>"[exact text]" or "Not applicable"</quote>
    <justification>[one sentence or "Not applicable"]</justification>
  </sq_2_5>
</domain2_conditional>"""

PROMPT_DOMAIN2_ANALYSIS = """You are an expert systematic reviewer applying the Cochrane Risk of Bias 2 (RoB 2) tool.

TRIAL: {intervention} vs {comparator} | Outcome: {outcome}

Read the following:

<statistical_analysis>
{analysis_text}
</statistical_analysis>

<results_participants>
{results_text}
</results_participants>

---

GUIDANCE FROM STERNE ET AL. 2019 SUPPLEMENT (Domain 2):

The effect of interest is: "{effect_of_interest}"

If effect_of_interest = "ITT" (assessing the effect of ASSIGNMENT to intervention):
  Q2.6 appropriate analyses:  ITT analysis, modified ITT (mITT) analysis
  Q2.6 inappropriate analyses: naive per-protocol analysis, as-treated analysis
  Source: Sterne et al. 2019 supplement, Domain 2 Part A.

If effect_of_interest = "per-protocol" (assessing the effect of ADHERING to intervention):
  Q2.6 appropriate analyses:  instrumental variable analyses (for single intervention,
    all-or-nothing adherence), inverse probability weighting (for sustained treatment strategies)
  Q2.6 inappropriate analyses: ITT analysis, naive per-protocol analysis, as-treated analysis
  Source: Sterne et al. 2019 supplement, Domain 2 Part B.

QUESTION 2.6: Was an APPROPRIATE ANALYSIS used to estimate the effect of ASSIGNMENT TO INTERVENTION (ITT effect)?

APPROPRIATE for ITT effect:
- Strict ITT: all randomized participants included regardless of adherence
- Modified ITT (mITT): excludes only participants with missing outcome data
- Post-randomization exclusions limited to independently determined ineligible participants

INAPPROPRIATE for ITT effect:
- Naive per-protocol analysis: excludes non-adherent participants by choice
- As-treated analysis: groups participants by what they received, not what they were assigned

Answer Y/PY if: paper describes an ITT or appropriate mITT approach.
Answer N/PN if: per-protocol or as-treated is the primary analysis.
Answer NI if: analysis method is not described.

IF 2.6 = Y/PY: set 2.7 to NA.
IF 2.6 = N/PN/NI: answer Q2.7.

QUESTION 2.7 [only if 2.6 = N/PN/NI]: Was there POTENTIAL FOR SUBSTANTIAL IMPACT of the failure to analyze by randomized group?

Answer Y/PY if: many participants excluded/misanalyzed, rare outcome, or exclusions related to prognostic factors.
Answer N/PN if: very few exclusions, common outcome, exclusions unrelated to outcome.

---

<domain2_analysis>
  <sq_2_6>
    <answer>[Y/PY/PN/N/NI]</answer>
    <quote>"[exact text]" ([Section])</quote>
    <justification>[one sentence]</justification>
  </sq_2_6>

  <sq_2_7>
    <answer>[Y/PY/PN/N/NI or NA]</answer>
    <quote>"[exact text]" or "Not applicable"</quote>
    <justification>[one sentence or "Not applicable"]</justification>
  </sq_2_7>
</domain2_analysis>"""

PROMPT_DOMAIN3 = """You are an expert systematic reviewer applying the Cochrane Risk of Bias 2 (RoB 2) tool.

TRIAL: {intervention} vs {comparator} | Outcome: {outcome} | N randomized: {n_randomized}

Read the following:

<consort_flow>
{consort_text}
</consort_flow>

<missing_data_handling>
{missing_data_text}
</missing_data_handling>

<sensitivity_analyses>
{sensitivity_text}
</sensitivity_analyses>

---

GUIDANCE FROM STERNE ET AL. 2019 SUPPLEMENT (Domain 3):

Regarding Q3.1 for time-to-event outcomes:
- Censored participants should be regarded as having missing outcome data (per Sterne et al.).
  However, "nearly all participants" means: did most participants either (a) have the event, or
  (b) have confirmed event-free follow-up to administrative censoring at study cut-off?
  Administrative censoring at study cut-off = outcome status IS known (absence of event to that
  date). This counts as data available.

Regarding Q3.4 ("Is it LIKELY that missingness depended on its true value?"):
Answer Y or PY ONLY when you identify at least one of these criteria from Sterne et al.:
  1. Differences between groups in PROPORTIONS of missing data
  2. Reported reasons for missing data suggest dependence on the true outcome value
  3. Reported reasons for missing data DIFFER between groups
  4. Trial circumstances make informative dropout likely (e.g., patients drop out because their
     condition is worsening, which directly relates to the outcome)
  5. In time-to-event analyses: censoring occurs because participants STOP OR CHANGE INTERVENTION
     due to factors related to the outcome (e.g., drug toxicity, switch to second-line treatment)
     AND those participants were NO LONGER FOLLOWED for the outcome after stopping.

IMPORTANT for criterion 5: If patients stopped the assigned treatment but continued to be
followed for the outcome (common in well-conducted trials), there is NO informative censoring —
their outcome data are not missing, only their treatment exposure changed.

If the only evidence is that censoring occurred (expected in all survival analyses), answer
Q3.4 = N/PN. Require specific evidence from criteria 1-5 above before answering Y/PY.

QUESTION 3.1: Were outcome data available for ALL or NEARLY ALL randomized participants?

"Nearly all" = >95% for continuous outcomes. For dichotomous outcomes, also check whether the number of missing participants is negligible relative to observed events (even <5% missing can matter if the event rate is very low). If you can calculate completeness from CONSORT numbers, do so and report it.

Answer Y/PY if: ≥95% with data, or missing is negligible relative to events.
Answer N/PN if: <95% with data, or missing is substantial relative to events.
Answer NI if: no information about outcome completeness.

IF 3.1 = Y/PY: set 3.2, 3.3, 3.4 to NA.
IF 3.1 = N/PN/NI: answer Q3.2.

QUESTION 3.2 [answer ONLY if 3.1 = N/PN/NI; otherwise answer NA]: Is there EVIDENCE that the result was NOT biased by missing outcome data?

ADEQUATE evidence: pre-specified sensitivity analyses (tipping-point, best/worst-case imputation), multiple imputation with appropriate assumptions, pattern-mixture models.
INADEQUATE alone: LOCF (last-observation-carried-forward), complete-case analysis without sensitivity analyses.

IF 3.2 = Y/PY: set 3.3 and 3.4 to NA.
IF 3.2 = N/PN: answer Q3.3.

QUESTION 3.3 [answer ONLY if 3.2 = N/PN; otherwise answer NA]: Could missingness in the outcome DEPEND ON ITS TRUE VALUE?

This asks whether the reason someone is missing could be related to their actual outcome value. Common examples: participants who worsened may have dropped out; participants who died can no longer contribute. If most withdrawals have documented reasons clearly unrelated to outcome (relocation, administrative reasons), answer N/PN.

IF 3.3 = N/PN: set 3.4 to NA.
IF 3.3 = Y/PY/NI: answer Q3.4.

QUESTION 3.4 [answer ONLY if 3.3 = Y/PY/NI; otherwise answer NA]: Is it LIKELY that missingness depended on its true value?

Note: This requires inference about unobserved mechanisms and is inherently uncertain. Set uncertainty_flag=HIGH unless you have clear direct evidence.

---

<domain3>
  <sq_3_1>
    <answer>[Y/PY/PN/N/NI]</answer>
    <quote>"[exact text]" ([Section])</quote>
    <completeness_calculation>[e.g. "234/249 = 94.0%" or "Not calculable from available text"]</completeness_calculation>
    <justification>[one sentence]</justification>
  </sq_3_1>

  <sq_3_2>
    <answer>[Y/PY/PN/N/NI or NA]</answer>
    <quote>"[exact text]" or "Not applicable"</quote>
    <justification>[one sentence or "Not applicable"]</justification>
  </sq_3_2>

  <sq_3_3>
    <answer>[Y/PY/PN/N/NI or NA]</answer>
    <quote>"[exact text]" or "Not applicable"</quote>
    <justification>[one sentence or "Not applicable"]</justification>
    <uncertainty_flag>[HIGH or NORMAL]</uncertainty_flag>
  </sq_3_3>

  <sq_3_4>
    <answer>[Y/PY/PN/N/NI or NA]</answer>
    <quote>"[exact text]" or "Not applicable"</quote>
    <justification>[one sentence or "Not applicable"]</justification>
    <uncertainty_flag>[HIGH or NORMAL]</uncertainty_flag>
  </sq_3_4>
</domain3>"""

PROMPT_DOMAIN4 = """You are an expert systematic reviewer applying the Cochrane Risk of Bias 2 (RoB 2) tool.

TRIAL: {intervention} vs {comparator} | Outcome: {outcome} | Outcome type: {outcome_type}
Q2.1 (participants aware of assignment): {sq_2_1}

Read the following:

<outcome_measurement>
{outcome_measurement_text}
</outcome_measurement>

<blinding_section>
{blinding_text}
</blinding_section>

---

QUESTION 4.1: Was the method of measuring the outcome INAPPROPRIATE?

This asks only about the measurement instrument/method — NOT whether the chosen outcome is the best research question. A validated surrogate measured with a well-established instrument is not flagged here.

Answer Y/PY ONLY if: the measurement instrument has known poor validity, is insensitive to plausible effects, or is entirely unsuited to the construct.
Answer N/PN in most cases where a standard validated instrument is used.

QUESTION 4.2: Could measurement or ascertainment HAVE DIFFERED BETWEEN INTERVENTION GROUPS?

Answer Y/PY if: different methods or frequencies of measurement in different arms; differential passive detection (e.g., more healthcare visits in one arm increasing adverse event detection).
Answer N/PN if: identical measurement procedures in both arms.

IF 4.1 OR 4.2 = Y/PY: set 4.3, 4.4, 4.5 to NA (domain is already High risk).
IF BOTH 4.1 AND 4.2 = N/PN/NI: answer Q4.3.

QUESTION 4.3 [answer ONLY if both 4.1 and 4.2 = N/PN/NI; otherwise answer NA]: Were OUTCOME ASSESSORS aware of the intervention received?
Answer Y/PY if: assessors explicitly knew assignments, or blinding was not attempted.
Answer N/PN if: assessors were blinded and blinding was maintained.

IF 4.3 = N/PN: set 4.4 and 4.5 to NA.
IF 4.3 = Y/PY/NI: answer Q4.4.

QUESTION 4.4 [answer ONLY if 4.3 = Y/PY/NI; otherwise answer NA]: Could knowledge of intervention have INFLUENCED THE ASSESSMENT?

For OBJECTIVE outcomes (all-cause mortality, centrally adjudicated imaging, lab values): answer N — knowledge cannot influence an objective fact.
For PATIENT-REPORTED outcomes (pain, nausea, QoL, fatigue): answer Y/PY — subjective self-report is directly shaped by expectation.
For CLINICIAN-ASSESSED outcomes (CTCAE grading, clinical response): answer Y/PY — clinical judgment is involved.

IF 4.4 = N/PN: set 4.5 to NA.
IF 4.4 = Y/PY/NI: answer Q4.5.

QUESTION 4.5 [answer ONLY if 4.4 = Y/PY/NI; otherwise answer NA]: Was assessment LIKELY influenced by knowledge of intervention?

Consider: strongly held beliefs about intervention superiority; whether assessors were also delivering the intervention.

GUIDANCE FROM STERNE ET AL. 2019 SUPPLEMENT (Domain 4):

Q4.4 ("Could assessment have been influenced?") vs Q4.5 ("Was it LIKELY influenced?"):

Q4.4: Addresses whether the outcome TYPE is susceptible to knowledge-of-assignment bias.
  Answer Y/PY for: participant-reported outcomes, observer-reported outcomes requiring judgment.
  Answer N/PN for: objective outcomes without judgment (e.g., all-cause mortality, clearly
    defined laboratory thresholds, imaging with pre-defined criteria).
  Source: Sterne et al. 2019 supplement, Domain 4.

Q4.5: Requires specific evidence of likely influence, not just open-label design.
  Per Sterne et al.: "When there is strong belief in the beneficial or harmful effects of an
  intervention, it is more likely that the outcome was influenced by knowledge of intervention."
  Answer N/PN for Q4.5 when: assessors used standardized, pre-defined grading criteria that
  constrain subjective judgment (e.g., CTCAE grading for adverse events, pre-defined lab
  thresholds), UNLESS there is specific evidence of differential application of those criteria.
  Open-label design alone and sponsor trial participation alone do NOT justify Q4.5 = Y/PY.
  Require concrete evidence of differential assessment before answering Y/PY.
  Source: Sterne et al. 2019 supplement, Domain 4.

---

<domain4>
  <sq_4_1>
    <answer>[Y/PY/PN/N/NI]</answer>
    <quote>"[exact text]" ([Section])</quote>
    <justification>[one sentence]</justification>
  </sq_4_1>

  <sq_4_2>
    <answer>[Y/PY/PN/N/NI]</answer>
    <quote>"[exact text]" ([Section])</quote>
    <justification>[one sentence]</justification>
  </sq_4_2>

  <sq_4_3>
    <answer>[Y/PY/PN/N/NI or NA]</answer>
    <auto_set_reason>[leave blank]</auto_set_reason>
    <quote>"[exact text]" or "Not applicable"</quote>
    <justification>[one sentence or "Not applicable"]</justification>
  </sq_4_3>

  <sq_4_4>
    <answer>[Y/PY/PN/N/NI or NA]</answer>
    <quote>"[exact text]" or "Not applicable"</quote>
    <justification>[one sentence or "Not applicable"]</justification>
  </sq_4_4>

  <sq_4_5>
    <answer>[Y/PY/PN/N/NI or NA]</answer>
    <quote>"[exact text]" or "Not applicable"</quote>
    <justification>[one sentence or "Not applicable"]</justification>
    <uncertainty_flag>[HIGH or NORMAL]</uncertainty_flag>
  </sq_4_5>
</domain4>"""

PROMPT_DOMAIN5 = """You are an expert systematic reviewer applying the Cochrane Risk of Bias 2 (RoB 2) tool.

TRIAL: {intervention} vs {comparator} | Outcome: {outcome}
Numerical result being assessed: {numerical_result}
Trial registration: {registration_number}
Registered primary endpoint: {registered_endpoint}
Reported primary endpoint: {reported_endpoint}

Read the following:

<registration_or_protocol>
{registration_text}
</registration_or_protocol>

<statistical_analysis_plan>
{sap_text}
</statistical_analysis_plan>

<results_section>
{results_text}
</results_section>

---

CRITICAL GUIDANCE ON Q5.1 (Sterne et al. 2019 supplement, Domain 5):

Q5.1 definition: "Were the data that produced THIS RESULT analysed in accordance with a
pre-specified analysis plan finalised before unblinded outcome data were available?"

This asks about ANY pre-specification — primary OR secondary endpoint.
Do NOT answer N/PN because the assessed outcome ({outcome}) is not the registered primary.

HOW TO ANSWER Q5.1:
Step 1 — Search {registration_text} directly for any mention of "{outcome}" or close synonyms.
  - Found as primary endpoint → Y
  - Found as secondary endpoint → Y or PY
  - Found as exploratory/tertiary only → PY
  - Not mentioned anywhere in registration text → NI (if no protocol available) or N (if
    registration clearly exists but outcome is absent from it)

Step 2 — Cross-reference the pre-extracted fields:
  - Registered primary: {registered_endpoint}
  - Registered secondary endpoints: {registered_secondary_endpoints}
  These are summaries only — always prioritise what you find in the raw registration text.

Step 3 — Answer N or PN ONLY if you have positive evidence that {outcome} was either
  (a) not mentioned anywhere in any pre-specified document, OR
  (b) the analysis approach was materially changed after seeing unblinded data.

Changes made before unblinding, or clearly unrelated to results, do not raise concerns.
Source: Sterne et al. 2019 supplement, Domain 5.

Q5.2: Selection from multiple outcome MEASUREMENTS within the same domain (different scales,
  definitions, time points for the same outcome). Answer NI if intentions unclear AND multiple
  measurement approaches existed.

Q5.3: Selection from multiple ANALYSES of the same data (adjusted vs unadjusted, different
  covariate sets, missing data handling). Answer NI if intentions unclear AND multiple
  analysis approaches were possible.

AUTHORITATIVE REGISTRATION DATA:
{ctgov_outcomes}

When this data is available, use it as the primary source for answering Q5.1.
If {outcome} appears in the PRIMARY list above → Q5.1 = Y
If {outcome} appears in the SECONDARY or EXPLORATORY list → Q5.1 = Y or PY
If registration data is available but {outcome} is NOT in any list → Q5.1 = N
If data is not available (lookup failed or no NCT number) → rely on the registration text below.

QUESTION 5.1: Were the data analyzed in accordance with a PRE-SPECIFIED ANALYSIS PLAN finalized BEFORE unblinded outcome data were available?

Answer Y/PY if: trial was prospectively registered with the outcome specified before completion; SAP was published or referenced prior to unblinding; analysis matches registered plan.
Answer N/PN if: clear evidence of post-hoc changes, endpoint switching, or analysis decided after seeing results.
Answer NI if: no registration, no SAP reference, no statement about pre-specification.

If a registration number is provided: explicitly compare the registered primary endpoint against what was actually reported and note any discrepancy.

QUESTION 5.2: Is the result likely to have been SELECTED FROM MULTIPLE ELIGIBLE OUTCOME MEASUREMENTS (scales, definitions, time points)?

Answer N/PN if: only one valid measurement approach was used, or all pre-specified measurements are reported.
Answer Y/PY if: multiple time points or scales were available but only the most favorable is selectively reported.
Answer NI if: it is unclear whether multiple measurement options existed.
Do NOT answer Y/PY merely because the assessed outcome is secondary or differs from the registered primary endpoint; that is not selective measurement unless there is evidence that eligible measurements of this same outcome were selectively chosen or omitted.

QUESTION 5.3: Is the result likely to have been SELECTED FROM MULTIPLE ELIGIBLE ANALYSES?

Answer N/PN if: analysis matches the pre-specified plan and no selective reporting is evident.
Answer Y/PY if: multiple analyses were conducted but only the favorable one is reported (e.g., only adjusted results shown when pre-specified primary was unadjusted).
Answer NI if: it is unclear whether multiple analyses were conducted.

---

<domain5>
  <sq_5_1>
    <answer>[Y/PY/PN/N/NI]</answer>
    <quote>"[exact text]" ([Section])</quote>
    <justification>[one sentence]</justification>
    <registration_comparison>[note any discrepancy between registered and reported primary endpoint, or "No registration information available"]</registration_comparison>
  </sq_5_1>

  <sq_5_2>
    <answer>[Y/PY/PN/N/NI]</answer>
    <quote>"[exact text]" or "No relevant text found"</quote>
    <justification>[one sentence]</justification>
  </sq_5_2>

  <sq_5_3>
    <answer>[Y/PY/PN/N/NI]</answer>
    <quote>"[exact text]" or "No relevant text found"</quote>
    <justification>[one sentence]</justification>
  </sq_5_3>
</domain5>"""
