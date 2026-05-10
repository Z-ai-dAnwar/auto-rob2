PROMPT_RCT_SCREEN = """You are a systematic review methodologist. Verify whether the input study is a randomized controlled trial before any RoB 2 assessment.

Read the following text carefully:

<methods_section>
{methods_text}
</methods_section>

RoB 2 applies only to randomized controlled trials: participants must be randomly assigned to intervention vs control/comparator groups. Random methods include a computer-generated sequence or computer-generated random numbers, random number tables, coin tossing, shuffling cards or envelopes, throwing dice, minimization with a random element, or drawing lots.

Studies that are not RCTs include observational studies, cohort studies, case-control studies, non-randomized experimental designs, and quasi-randomized trials where allocation is predictable, such as alternation, date of birth, admission date, record number, clinician judgment, or intervention availability.

If the study is not randomized, stop the assessment and state that ROBINS-I, not RoB 2, should be used.

Respond in this exact XML format:

<screening>
  <is_rct>YES or NO</is_rct>
  <evidence>"[exact quote from text supporting your decision]"</evidence>
  <study_design>[brief description of the study design as reported]</study_design>
  <note>[if NO: state that ROBINS-I should be used instead; if YES: leave blank]</note>
</screening>"""

PROMPT_PRELIMINARY_INFO = """You are an expert systematic reviewer applying the Cochrane Risk of Bias 2 (RoB 2) tool. Before answering signaling questions, collect the preliminary information required by RoB 2.

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

Extract the experimental intervention, comparator intervention, outcome being assessed, numerical result, effect-relevant analysis details, trial registration, and source information. RoB 2 is result-specific, not trial-wide; if no user-specified outcome is available, use the primary outcome. If co-primary endpoints are apparent and the target outcome is unclear, identify the selected outcome and mark uncertainty in the quote/justification fields.

For every extracted value, provide the exact quoted text from the available source. Do not paraphrase quotes. If genuinely absent, write "Not reported" for the value and "No relevant text found" for the quote.

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
    <value>[specific outcome; use the primary outcome if user did not specify another]</value>
    <quote>"[exact text]" ([Section])</quote>
    <is_primary>YES or NO or UNCLEAR</is_primary>
  </outcome_assessed>

  <outcome_type>Classify the outcome type using exactly one of these five values:
  - vital-status: all-cause mortality or disease-specific mortality assessed as a single criterion: death is the only event that counts. Do not use this category for composite endpoints that combine death with non-mortality criteria such as progression, relapse, or hospitalisation, even if death is one component.
  - biomarker: laboratory or imaging measurement with a pre-defined numerical threshold
  - clinician-composite: composite or time-to-event outcome requiring clinical or radiological judgment
  - clinician-graded: outcome assessed using a standardized clinical grading scale that still requires judgment
  - patient-reported: outcome assessed by the participant using a questionnaire or self-report instrument
  Examples: all-cause mortality = `vital-status`; Event-free survival combining death with relapse, progression, or hospitalisation = `clinician-composite`; clinician-rated symptom or function scale = `clinician-graded`; participant questionnaire = `patient-reported`.
</outcome_type>

  <numerical_result>
    <value>[effect estimate with CI, e.g., HR 0.64 (95% CI 0.54-0.77)]</value>
    <quote>"[exact text]" ([Section])</quote>
  </numerical_result>

  <n_randomized>
    <value>[total number randomized, as integer string]</value>
    <quote>"[exact text]" ([Section])</quote>
  </n_randomized>

  <trial_registration>
    <number>[registration number or "Not reported"]</number>
    <registry>[ClinicalTrials.gov or ISRCTN or other registry or "Not reported"]</registry>
    <quote>"[exact text]" or "Not reported"</quote>
  </trial_registration>

  <registered_primary_endpoint>
    <value>[primary endpoint listed in trial registry or protocol]</value>
    <quote>"[exact text]" ([Section])</quote>
  </registered_primary_endpoint>

  <registered_secondary_endpoints>List any secondary or co-primary endpoints from the registration or protocol exactly as stated. Separate multiple endpoints with semicolons. If none found, write "Not reported".</registered_secondary_endpoints>

  <registered_analysis>
    <value>[pre-specified analysis approach from registry/protocol, e.g., ITT or per-protocol]</value>
    <quote>"[exact text]" ([Section])</quote>
  </registered_analysis>
</preliminary_info>

RULES:
- Every quote must be the exact source text, not a paraphrase.
- Do not guess numerical results.
- Use "No relevant text found" only when the available sources genuinely do not contain the information."""

PROMPT_DOMAIN1 = """You are an expert systematic reviewer applying the Cochrane Risk of Bias 2 (RoB 2) tool.

TRIAL: {intervention} vs {comparator} | Outcome: {outcome}

Read the following evidence. The Primary Evidence section was extracted specifically for this domain. Use it as your primary source. The Additional Retrieved Context supplements it; it may contain supporting detail not present in the primary section.

=== PRIMARY EVIDENCE (domain-extracted - treat as authoritative) ===

<randomization_section>
{randomization_text}
</randomization_section>

<baseline_characteristics>
{baseline_text}
</baseline_characteristics>

<consort_flow>
{consort_text}
</consort_flow>

<registry_design_metadata>
{ctgov_design}
</registry_design_metadata>

=== ADDITIONAL RETRIEVED CONTEXT (full-document search) ===
{rag_text}

Answer Domain 1 signaling questions: Bias arising from the randomization process.

If ClinicalTrials.gov design metadata is provided above, treat it as authoritative evidence about the trial's registered design:
- An allocation type of RANDOMIZED is evidence that the registry classifies the trial as randomized; without sequence-generation details, this supports PY rather than Y for Q1.1.
- Masking = NONE confirms an open-label design, which is context for assessors but is not directly scored in D1.
- Presence of a DMC or a research network lead sponsor is contextual registry information only; do not treat it as direct evidence of allocation concealment unless the paper or registry also describes a concealment or central allocation process.
- Use NI only when both the paper text and registry metadata provide no meaningful basis for a judgment.

For each question, choose exactly one answer: Y, PY, PN, N, or NI.
Y/N means firm evidence is stated. PY/PN means a reasonable inference from indirect evidence. NI is reserved for genuine absence of enough information; it is not a default.

1.1 Was the allocation sequence random?
- Y: a recognized random method was explicitly described, such as computer-generated random numbers, random number table, coin tossing, shuffling cards or envelopes, dice, minimization with a random element, or drawing lots.
- PY: a large, well-conducted trial lacks specific sequence details but has no indication of a non-random method.
- PN: prior/contextual evidence suggests possible non-random methods and the current report does not clarify.
- N: the sequence was non-random or predictable, such as alternation, dates, record numbers, clinician or participant decisions, availability, or any systematic/haphazard method.
- NI: the report only states that the study was randomized with no details or contextual basis for a probable judgment.

1.2 Was the allocation sequence concealed until participants were enrolled and assigned to interventions?
- Y: remote or centrally administered allocation, independent central pharmacy, telephone/internet randomization, or correctly used sealed opaque sequentially numbered envelopes/containers.
- PY: adequate concealment is strongly implied, for example a statement of concealed allocation without exact operational detail.
- PN: the method is described incompletely and suggests possible inadequacy, such as envelopes without enough safeguards.
- N: enrolling investigators or participants could know or predict the forthcoming allocation.
- NI: no useful information about allocation concealment is provided.

For large multicenter cooperative-group trials with stratified randomization, balanced groups, and no suggestion that recruiters could foresee assignments, answer PY rather than NI for Q1.2 even if the exact operational concealment mechanism is not named. Reserve NI for reports that only say randomized and provide no trial-infrastructure, stratification, or baseline-balance context.

1.3 Did baseline differences between intervention groups suggest a problem with the randomization process?
Baseline differences compatible with chance do not indicate bias.
- Y: substantial group-size discrepancies relative to intended allocation ratio; an excess of statistically significant baseline differences beyond chance; imbalance in key prognostic factors or baseline outcome measures large enough to bias the effect estimate; or excessive similarity incompatible with chance.
- PY: indications suggest a possible randomization problem but are not conclusive.
- PN: minor baseline concerns are unlikely to introduce material bias.
- N: no important imbalances are apparent or observed imbalances are compatible with chance.
- NI: no useful baseline information is available.

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

TRIAL: {intervention} vs {comparator} | Outcome: {outcome} | Effect of interest: effect of assignment to intervention (intention-to-treat)

Read the following evidence. The Primary Evidence section was extracted specifically for this domain. Use it as your primary source. The Additional Retrieved Context supplements it; it may contain supporting detail not present in the primary section.

=== PRIMARY EVIDENCE (domain-extracted - treat as authoritative) ===

<blinding_section>
{blinding_text}
</blinding_section>

<methods_interventions>
{methods_text}
</methods_interventions>

<registry_design_metadata>
{ctgov_design}
</registry_design_metadata>

=== ADDITIONAL RETRIEVED CONTEXT (full-document search) ===
{rag_text}

Answer the first two Domain 2 signaling questions: Bias due to deviations from intended interventions.

Important RoB 2 principle: an open-label trial is not automatically high risk. Risk depends on whether awareness led to deviations from intended interventions that arose because of the trial context, whether those deviations affected the outcome, whether they were balanced, and whether the analysis was appropriate.

If ClinicalTrials.gov design metadata is provided above, use the masking field as authoritative confirmation when it maps to the person being assessed: masking = NONE confirms participants and carers were aware of their assignment (supports Y for Q2.1 and Q2.2). For blinded designs, check any listed masked parties before judging participants separately from carers or intervention deliverers.

2.1 Were participants aware of their assigned intervention during the trial?
- Y: participants were explicitly aware; the intervention made blinding impossible; or intervention-specific side effects/toxicities revealed assignment.
- PY: design or side effects likely allowed participants to guess assignment, or blinding was attempted but likely ineffective.
- PN: blinding was used but not verified, interventions were similar, or no evidence of compromised participant blinding is reported.
- N: participants were explicitly and successfully blinded, or robust indistinguishable placebo/sham procedures were used and verified.
- NI: participant awareness or blinding is not reported and cannot be inferred.

2.2 Were carers and people delivering the interventions aware of participants' assigned intervention during the trial?
- Y: carers/deliverers were explicitly aware; blinding was impossible; visible side effects revealed assignment; or allocation was not concealed from care staff.
- PY: design or side effects likely revealed assignment to carers/deliverers.
- PN: blinding methods for carers/deliverers were described but not verified, or interventions were similar enough that awareness was unlikely.
- N: carers/deliverers were explicitly and successfully blinded, or robust blinding was implemented and verified.
- NI: awareness of carers/deliverers is not reported and cannot be inferred.

If both 2.1 and 2.2 are N/PN, 2.3-2.5 are not applicable and the pipeline will skip them.

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

Read the following evidence. The Primary Evidence section was extracted specifically for this domain. Use it as your primary source. The Additional Retrieved Context supplements it; it may contain supporting detail not present in the primary section.

=== PRIMARY EVIDENCE (domain-extracted - treat as authoritative) ===

<protocol_adherence>
{deviations_text}
</protocol_adherence>

<concomitant_medications>
{concomitant_text}
</concomitant_medications>

=== ADDITIONAL RETRIEVED CONTEXT (full-document search) ===
{rag_text}

Because 2.1 or 2.2 was Y/PY/NI, answer the conditional Domain 2 questions for the effect of assignment to intervention.

Important RoB 2 principle: NI is a last resort. Do not use NI merely because a report omits an explicit statement that routine clinical-management events were unrelated to trial context when N or PN is a reasonable inference.

2.3 Were there deviations from the intended intervention that arose because of the trial context?
This question concerns changes from assigned intervention that are inconsistent with the protocol and occurred because of the trial context, such as recruitment, engagement, unblinding, or trial personnel undermining protocol implementation in ways that would not happen outside the trial. Do not count protocol-consistent changes such as dose cessation for toxicity, treatment changes after outcome events, or additional interventions used to treat consequences of the assigned intervention.
- Y: clear evidence that trial context caused protocol-inconsistent deviations or non-protocol interventions.
- PY: strong indications that recruitment, engagement, unblinding, or trial personnel led to protocol-inconsistent intervention changes or influenced adherence in ways that would not happen outside the trial.
- PN: deviations appear consistent with what could occur outside the trial context, or no indication suggests trial-context influence.
- N: deviations are explicitly unrelated to trial context, are protocol-consistent changes, or reflect normal clinical management that could occur outside the trial context.
- NI: use only when deviations are described but the available sources genuinely do not allow a reasonable PY or PN judgment about whether they arose because of the trial context.

If 2.3 is N/PN/NI, answer 2.4 and 2.5 as NA.

2.4 If Y/PY to 2.3: Were these deviations likely to have affected the outcome?
- Y: clear evidence deviations affected the outcome, or large protocol-inconsistent changes likely altered outcomes.
- PY: deviations were substantial and plausibly affect the assessed outcome.
- PN: deviations were minimal or unlikely to influence the assessed outcome.
- N: deviations were minor, unrelated to the outcome, or shown not to affect the outcome.
- NI: deviations are described but their outcome impact cannot be determined.

If 2.4 is N/PN/NA, answer 2.5 as NA. If 2.4 is Y/PY/NI, answer 2.5.

2.5 If Y/PY/NI to 2.4: Were these deviations from intended intervention balanced between groups?
- Y: clear evidence deviations were equally distributed or balanced by design.
- PY: data suggest similar patterns of deviations across groups.
- PN: data suggest different patterns, but not conclusively.
- N: clear evidence of unequal distribution.
- NI: deviations are known or likely to affect the outcome, but their distribution between groups is not reported.

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

PROMPT_DOMAIN2_ADHERING_CONDITIONAL = """You are an expert systematic reviewer applying the Cochrane Risk of Bias 2 (RoB 2) tool.

TRIAL: {intervention} vs {comparator} | Outcome: {outcome}
Prior answers: Q2.1 = {sq_2_1} | Q2.2 = {sq_2_2}
Effect of interest: effect of adhering to intervention (per-protocol)

Read the following evidence. The Primary Evidence section was extracted specifically for this domain. Use it as your primary source. The Additional Retrieved Context supplements it; it may contain supporting detail not present in the primary section.

=== PRIMARY EVIDENCE (domain-extracted - treat as authoritative) ===

<protocol_adherence>
{deviations_text}
</protocol_adherence>

<concomitant_medications>
{concomitant_text}
</concomitant_medications>

=== ADDITIONAL RETRIEVED CONTEXT (full-document search) ===
{rag_text}

Answer the Domain 2 Version B conditional questions for bias due to deviations from intended interventions when estimating the effect of adhering to intervention.

2.3 If applicable, if Y/PY/NI to 2.1 or 2.2: Were important non-protocol interventions balanced across intervention groups?
Important non-protocol interventions are additional interventions or exposures that are inconsistent with the trial protocol, may be received with or after starting assigned intervention, and are prognostic for the outcome.
- Y: important non-protocol interventions were clearly balanced.
- PY: available data suggest balance.
- PN: available data suggest imbalance, but not conclusively.
- N: important non-protocol interventions were clearly not balanced.
- NI: insufficient information to judge balance.
- NA: not applicable because the assessment is not addressing non-protocol interventions or participants/carers/deliverers were unaware.

2.4 If applicable: Were there failures in implementing the intervention that could have affected the outcome?
- Y: implementation failures clearly could have affected the outcome.
- PY: implementation failures probably could have affected the outcome.
- PN: implementation was mostly successful or failures were unlikely to affect the outcome.
- N: no relevant implementation failures occurred or they could not affect the outcome.
- NI: insufficient information about implementation failures.
- NA: not applicable because this deviation type is not being assessed.

2.5 If applicable: Was there non-adherence to the assigned intervention regimen that could have affected participants' outcomes?
Non-adherence includes imperfect compliance, intervention cessation, crossovers to comparator intervention, and switches to another active intervention.
- Y: non-adherence clearly could have affected outcomes.
- PY: non-adherence probably could have affected outcomes.
- PN: non-adherence was limited or unlikely to affect outcomes.
- N: participants adhered to the assigned regimen, or adherence issues could not affect outcomes.
- NI: insufficient information about adherence.
- NA: not applicable because this deviation type is not being assessed.

<domain2_conditional>
  <sq_2_3>
    <answer>[Y/PY/PN/N/NI or NA]</answer>
    <quote>"[exact text]" ([Section]) or "Not applicable"</quote>
    <justification>[one sentence or "Not applicable"]</justification>
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
Effect of interest in pipeline state: {effect_of_interest}

Read the following evidence. The Primary Evidence section was extracted specifically for this domain. Use it as your primary source. The Additional Retrieved Context supplements it; it may contain supporting detail not present in the primary section.

=== PRIMARY EVIDENCE (domain-extracted - treat as authoritative) ===

<statistical_analysis>
{analysis_text}
</statistical_analysis>

<results_participants>
{results_text}
</results_participants>

=== ADDITIONAL RETRIEVED CONTEXT (full-document search) ===
{rag_text}

Answer Domain 2 analysis questions for the effect of assignment to intervention unless the user explicitly configured a per-protocol/adhering effect. For assignment/ITT, appropriate analyses include strict ITT, modified ITT excluding only participants with missing outcome data, and post-randomization exclusions limited to independently determined ineligible participants. Naive per-protocol, as-treated, and analyses excluding eligible participants post-randomization are inappropriate for the assignment effect.

2.6 Was an appropriate analysis used to estimate the effect of assignment to intervention?
- Y: clear ITT analysis, appropriate mITT, or exclusions limited to independently determined ineligible participants.
- PY: analysis appears to follow ITT/mITT principles but lacks full detail, with only minimal likely irrelevant exclusions.
- PN: analysis suggests deviation from ITT principles or some inappropriate exclusions/regrouping.
- N: naive per-protocol, as-treated, analysis by treatment received, or substantial post-randomization exclusions of eligible participants.
- NI: analysis method is not specified or cannot be assessed.

If 2.6 is Y/PY, answer 2.7 as NA.

2.7 If N/PN/NI to 2.6: Was there potential for a substantial impact of failure to analyse participants in the group to which they were randomized?
- Y: many participants were excluded or analysed in the wrong group, outcome is rare, or exclusions/misclassification are related to prognostic factors.
- PY: a moderate number of exclusions/misanalyses could affect the result.
- PN: only a small number of participants were affected and a material effect is unlikely.
- N: very few/no participants were affected, or effects are clearly unrelated to prognosis/outcome.
- NI: insufficient information about exclusions or wrong-group analyses.

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

PROMPT_DOMAIN2_ADHERING_ANALYSIS = """You are an expert systematic reviewer applying the Cochrane Risk of Bias 2 (RoB 2) tool.

TRIAL: {intervention} vs {comparator} | Outcome: {outcome}
Effect of interest in pipeline state: {effect_of_interest}

Read the following evidence. The Primary Evidence section was extracted specifically for this domain. Use it as your primary source. The Additional Retrieved Context supplements it; it may contain supporting detail not present in the primary section.

=== PRIMARY EVIDENCE (domain-extracted - treat as authoritative) ===

<statistical_analysis>
{analysis_text}
</statistical_analysis>

<results_participants>
{results_text}
</results_participants>

=== ADDITIONAL RETRIEVED CONTEXT (full-document search) ===
{rag_text}

Answer Domain 2 Version B analysis question for the effect of adhering to intervention. Naive per-protocol analyses, as-treated analyses, ITT analyses, and analysis by treatment received will usually be inappropriate for estimating the effect of adhering to intervention. Appropriate methods may include instrumental variable analyses for a single all-or-nothing baseline intervention, or inverse probability weighting to adjust for censoring of participants who cease adherence in sustained treatment strategies. Such methods depend on strong assumptions that should be appropriate and justified.

2.6 Was an appropriate analysis used to estimate the effect of adhering to the intervention?
- Y: an appropriate causal method for the adherence effect was clearly used and justified, such as suitable instrumental variable analysis or inverse probability weighting.
- PY: an appropriate adherence-effect method appears to have been used, but some assumptions/details are unclear.
- PN: the analysis is probably inappropriate or insufficiently justified for the adherence effect.
- N: ITT, naive per-protocol, as-treated, analysis by treatment received, or another inappropriate method was used.
- NI: insufficient information to judge whether the adherence-effect analysis was appropriate.

2.7 is not applicable for the effect of adhering to intervention; answer NA.

<domain2_analysis>
  <sq_2_6>
    <answer>[Y/PY/PN/N/NI]</answer>
    <quote>"[exact text]" ([Section])</quote>
    <justification>[one sentence]</justification>
  </sq_2_6>
  <sq_2_7>
    <answer>NA</answer>
    <quote>Not applicable</quote>
    <justification>Not applicable for effect of adhering to intervention.</justification>
  </sq_2_7>
</domain2_analysis>"""

PROMPT_DOMAIN3 = """You are an expert systematic reviewer applying the Cochrane Risk of Bias 2 (RoB 2) tool.

TRIAL: {intervention} vs {comparator} | Outcome: {outcome} | N randomized: {n_randomized}

Read the following evidence. The Primary Evidence section was extracted specifically for this domain. Use it as your primary source. The Additional Retrieved Context supplements it; it may contain supporting detail not present in the primary section.

=== PRIMARY EVIDENCE (domain-extracted - treat as authoritative) ===

<consort_flow>
{consort_text}
</consort_flow>

<missing_data_handling>
{missing_data_text}
</missing_data_handling>

<sensitivity_analyses>
{sensitivity_text}
</sensitivity_analyses>

<registry_participant_flow>
{ctgov_flow}
</registry_participant_flow>

=== ADDITIONAL RETRIEVED CONTEXT (full-document search) ===
{rag_text}

Answer Domain 3 signaling questions: Bias due to missing outcome data.

3.1 Were data for this outcome available for all, or nearly all, participants randomized?
Nearly all means the number with missing outcome data is sufficiently small that their outcomes could have made no important difference. For continuous outcomes, 95 percent availability is often sufficient. For dichotomous outcomes, compare missing participants with observed events. Imputed data are missing data for this question.
- Y: data available for all randomized participants, or enough participants have data that missing outcomes could not materially affect the result.
- PY: data are available for nearly all participants and missingness is unlikely to matter.
- PN: noticeable missing data may affect the result.
- N: a significant proportion of outcome data is missing or imputed in place of observed data.
- NI: the extent of missing outcome data is not reported.

If ClinicalTrials.gov participant flow data is provided above, use it as supporting participant disposition evidence for Q3.1. Do not assume treatment completion equals outcome-data availability; compare it with paper text about the assessed outcome and missing outcome data.

If 3.1 is Y/PY, answer 3.2-3.4 as NA.

3.2 If N/PN/NI to 3.1: Is there evidence that the result was not biased by missing outcome data?
Adequate evidence may come from analysis methods that correct for bias or sensitivity analyses showing little change under plausible assumptions. LOCF or multiple imputation based only on intervention group should not be assumed to correct bias.
- Y: convincing correction methods and sensitivity analyses show no material bias.
- PY: appropriate methods or sensitivity analyses suggest minimal impact, with residual uncertainty.
- PN: methods are inadequate, poorly described, or limited.
- N: no adequate attempt to address missing-data bias, or sensitivity analyses show potential bias.

If 3.2 is Y/PY, answer 3.3-3.4 as NA. If 3.2 is N/PN, answer 3.3.

3.3 If N/PN to 3.2: Could missingness in the outcome depend on its true value?
- Y: loss to follow-up/withdrawal is clearly related to health status or outcome; time-to-event censoring may be outcome-related.
- PY: reasons are ambiguous or could plausibly relate to true outcome.
- PN: most missingness has documented reasons unlikely to relate to true outcome.
- N: all missingness is clearly unrelated to the outcome, such as technical failure or administrative interruption.
- NI: reasons/patterns are not described.

If 3.3 is N/PN, answer 3.4 as NA. If 3.3 is Y/PY/NI, answer 3.4.

3.4 If Y/PY/NI to 3.3: Is it likely that missingness in the outcome depended on its true value?
Reasons include differences between groups in missing-data proportions, reasons suggesting outcome-dependence, reasons differing between groups, trial circumstances making outcome-dependent missingness likely, or time-to-event censoring when participants stop/change assigned intervention for outcome-related reasons.
Per the RoB 2 supplement, five specific reasons support answering Y: (1) differences between groups in proportions of missing outcome data; (2) reported reasons for missingness provide evidence of outcome-dependence; (3) reported reasons differ between groups; (4) trial circumstances make outcome-dependent missingness likely; (5) in time-to-event analyses, participants' follow-up is censored when they stop or change their assigned intervention, for example because of drug toxicity or other context-specific outcome-related treatment changes.
For time-to-event outcomes, check whether rates of censoring differ between intervention groups — a difference in censoring rates supports answering Y or PY.
- Y: clear evidence makes outcome-dependent missingness likely.
- PY: some evidence suggests outcome-dependent missingness.
- PN: reasons/patterns mostly argue against likely outcome-dependence.
- N: evidence indicates missingness is independent of true outcome.
- NI: insufficient information to judge likelihood.

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
Q2.1 participants aware of assignment: {sq_2_1}

Read the following evidence. The Primary Evidence section was extracted specifically for this domain. Use it as your primary source. The Additional Retrieved Context supplements it; it may contain supporting detail not present in the primary section.

=== PRIMARY EVIDENCE (domain-extracted - treat as authoritative) ===

<outcome_measurement>
{outcome_measurement_text}
</outcome_measurement>

<blinding_section>
{blinding_text}
</blinding_section>

=== ADDITIONAL RETRIEVED CONTEXT (full-document search) ===
{rag_text}

Answer Domain 4 signaling questions: Bias in measurement of the outcome.

Outcome-specific instruction: first identify the outcome currently being assessed: {outcome}. When the outcome_measurement evidence contains definitions for multiple outcomes, answer based only on the definition for {outcome}. Do not anchor Domain 4 reasoning to a different endpoint, even if that endpoint is described first or in more detail.

4.1 Was the method of measuring the outcome inappropriate?
This asks about the measurement method, not whether the outcome itself is clinically ideal.
- Y: method is clearly insensitive to plausible effects, invalid, or inappropriate for the outcome.
- PY: strong indications the method may not detect relevant changes or validity is questionable.
- PN: method appears suitable but with limited detail or minor uncertainty.
- N: method is pre-specified, validated, standard, and appropriate.
- NI: insufficient detail about the measurement method.

4.2 Could measurement or ascertainment of the outcome have differed between intervention groups?
- Y: different methods, thresholds, timing, visit frequency, or diagnostic opportunities between groups.
- PY: possible differences in measurement/timing/detection opportunities.
- PN: methods appear consistent with minor uncertainty.
- N: identical methods, thresholds, and comparable timing across groups.
- NI: insufficient information to determine whether ascertainment differed.

If 4.1 or 4.2 is Y/PY, answer 4.3-4.5 as NA.

4.3 If N/PN/NI to 4.1 and 4.2: Were outcome assessors aware of the intervention received by study participants?
For participant-reported outcomes, the participant is the outcome assessor.
- Y: assessors were aware; blinding impossible; or for participant-reported outcomes participants knew/could not avoid knowing assignment.
- PY: assessors likely knew assignment but this is not explicit.
- PN: assessor blinding likely but not explicitly verified.
- N: assessors were blinded to intervention assignment.
- NI: assessor awareness is not reported and cannot be inferred from any available evidence.

Inference rule: If the trial is open-label (Q2.1=Y as shown in the context above) and the report contains no mention of a central blinded outcome adjudication committee or independent blinded assessors, answer PY (assessors likely aware of assignment) rather than NI. Reserve NI for cases where the blinding status of outcome assessors genuinely cannot be inferred, which is unusual once Q2.1=Y is established.

If 4.3 is N/PN, answer 4.4-4.5 as NA.

4.4 If Y/PY/NI to 4.3: Could assessment of the outcome have been influenced by knowledge of intervention received?
Knowledge can influence participant-reported outcomes, observer-reported outcomes involving judgment, and intervention-provider decision outcomes. It is unlikely to influence observer-reported outcomes that do not involve judgment, such as all-cause mortality.
Answer N or PN when the outcome is physiologically determined, mechanically measured, centrally blinded, or otherwise not plausibly susceptible to assessor knowledge. Answer Y or PY when the outcome assessment involves judgment that could plausibly be influenced by knowledge of intervention assignment.
- Y: outcome is clearly subjective or requires major judgment.
- PY: outcome includes subjective/judgmental elements despite standardization.
- PN: outcome is mostly objective with limited room for judgment.
- N: outcome is objective and cannot plausibly be influenced by knowledge of assignment.
- NI: insufficient information about the assessment process.

If 4.4 is N/PN, answer 4.5 as NA.

4.5 If Y/PY/NI to 4.4: Is it likely that assessment of the outcome was influenced by knowledge of intervention received?
This question distinguishes "could have been influenced" (Some concerns when Q4.5=N/PN) from "likely was influenced" (High when Q4.5=Y/PY/NI). High requires strong levels of belief in either beneficial or harmful effects of the intervention, for example patient-reported symptoms in trials of homeopathy, or assessments of recovery by a physiotherapist who delivered the intervention. When standardized outcome criteria are applied without evidence of strong beliefs, direct assessor involvement in delivering the intervention, or other mechanisms making influence likely, answer N or PN rather than Y or PY.
- Y: strong beliefs or direct assessor involvement make influence likely.
- PY: moderate evidence suggests likely influence.
- PN: little evidence of likely influence; standardized outcome criteria, safeguards, or absence of known strong prior beliefs reduce concern.
- N: no apparent mechanism or evidence of likely influence.
- NI: insufficient information about beliefs, expectations, or assessor role.

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
    <auto_set_reason>[leave blank unless pipeline auto-set this answer]</auto_set_reason>
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

TRIAL: {intervention} vs {comparator} | Outcome: {outcome} | Outcome type: {outcome_type}
Numerical result being assessed: {numerical_result}
Trial registration: {registration_number}
Registered primary endpoint: {registered_endpoint}
Reported outcome being assessed: {reported_endpoint}

Read the following evidence. The Primary Evidence section was extracted specifically for this domain. Use it as your primary source. The Additional Retrieved Context supplements it; it may contain supporting detail not present in the primary section.

=== PRIMARY EVIDENCE (domain-extracted - treat as authoritative) ===

Registered primary endpoint: {registered_endpoint}
Registered secondary endpoints: {registered_secondary_endpoints}

<registration_or_protocol>
{registration_text}
</registration_or_protocol>

<statistical_analysis_plan>
{sap_text}
</statistical_analysis_plan>

<results_section>
{results_text}
</results_section>

<authoritative_registration_outcomes>
{ctgov_outcomes}
</authoritative_registration_outcomes>

<authoritative_registration_description>
{ctgov_description}
</authoritative_registration_description>

=== ADDITIONAL RETRIEVED CONTEXT (full-document search) ===
{rag_text}

Answer Domain 5 signaling questions: Bias in selection of the reported result.

If a trial registration number is available, compare the registry/protocol outcomes and analysis intentions against the result being assessed. Focus on whether the numerical result was selected on the basis of the results, not merely whether the assessed outcome was primary or secondary.

5.1 Were the data that produced this result analysed in accordance with a pre-specified analysis plan finalized before unblinded outcome data were available for analysis?
- Y: detailed plan finalized before unblinded outcome data were available and analysis followed it.
- PY: strong indication of pre-specification, with some detail missing or minor justified deviations.
- PN: plan is mentioned but not detailed enough, or unexplained deviations suggest possible post hoc decisions.
- N: clear post hoc analysis decisions, endpoint switching, or result-based changes.
- NI: no adequate information on pre-specified analysis intentions or timing.

Answer Y or PY for 5.1 if a trial registration number is cited and the registration predates the primary analysis, or if the paper explicitly states that primary endpoints or the statistical analysis plan were prespecified or publicly available. Do not require every statistical detail, such as covariate lists, imputation methods, or sensitivity analyses, to be reprinted in the paper itself. A registration number combined with a prespecification claim is sufficient for Y. Answer PN only if there is specific evidence that the analysis plan changed after data unblinding, or if no registration exists and no prespecification is documented anywhere.

If a ClinicalTrials.gov registry description is provided above and lists PRIMARY, SECONDARY, or TERTIARY objectives, treat these as evidence that objectives were described in the registry. Objectives alone are not the same as prespecified endpoint definitions or a finalized pre-unblinding statistical analysis plan; use them together with protocol, SAP, amendment, and results-reporting evidence when judging Q5.1.

5.2 Is the numerical result being assessed likely to have been selected, on the basis of the results, from multiple eligible outcome measurements within the outcome domain?
Examples include different scales, definitions, or time points.
A pre-specified composite endpoint is NOT multiple eligible outcome measurements merely because it combines several components into one measure. Answer Q5.2=N for composite endpoints unless there is evidence that specific components were selected post-hoc. Answer Q5.2=Y/PY only when the paper reports one specific scale, definition, component, or time point chosen from several separately pre-specified alternatives based on the observed results.
- Y: multiple eligible measurements were available, only a subset is reported without justification, and selection based on favorability/significance is clear.
- PY: multiple measurements were likely available and reporting appears potentially selective.
- PN: most intended measurements are reported or omissions are explained.
- N: all intended eligible measurements are reported, only one measurement was possible, or inconsistencies are unrelated to results.
- NI: analysis intentions are unavailable/insufficient and more than one eligible measurement could have existed.

5.3 Is the numerical result being assessed likely to have been selected, on the basis of the results, from multiple eligible analyses of the data?
Examples include adjusted vs unadjusted models, different covariates, final value vs change score, transformations, cut-points, composite definitions, or missing-data strategies.
- Y: multiple eligible analyses were available, only a subset is reported without justification, and selection based on favorability/significance is clear.
- PY: multiple analyses likely existed and reporting appears potentially selective.
- PN: intended analyses are mostly reported or omissions are explained.
- N: all intended eligible analyses are reported, only one analysis was possible, or inconsistencies are unrelated to results.
- NI: analysis intentions are unavailable/insufficient and multiple eligible analyses could have existed.

<domain5>
  <sq_5_1>
    <answer>[Y/PY/PN/N/NI]</answer>
    <quote>"[exact text]" ([Section])</quote>
    <justification>[one sentence]</justification>
    <registration_comparison>[note any discrepancy between registered and reported endpoint/analysis, or "No registration information available"]</registration_comparison>
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
