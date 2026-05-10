"""Tests for prompt CT.gov metadata insertion points."""


def test_prompt_domain1_accepts_ctgov_design():
    from rob2_pipeline.prompts import PROMPT_DOMAIN1

    result = PROMPT_DOMAIN1.format(
        intervention="Docetaxel + ADT",
        comparator="ADT alone",
        outcome="Overall Survival",
        randomization_text="Patients were randomized.",
        baseline_text="",
        consort_text="",
        rag_text="",
        ctgov_design="Authoritative ClinicalTrials.gov registry design metadata:\n  Allocation type: RANDOMIZED",
    )

    assert "RANDOMIZED" in result
    assert "registry" in result.lower()


def test_prompt_domain2_sq12_accepts_ctgov_design():
    from rob2_pipeline.prompts import PROMPT_DOMAIN2_SQ12

    result = PROMPT_DOMAIN2_SQ12.format(
        intervention="Docetaxel + ADT",
        comparator="ADT alone",
        outcome="Overall Survival",
        blinding_text="Open-label trial.",
        methods_text="",
        rag_text="",
        ctgov_design="  Masking: NONE (masked parties: not specified)",
    )

    assert "NONE" in result


def test_registry_prompt_guidance_does_not_overclaim_indirect_metadata():
    from rob2_pipeline.prompts import PROMPT_DOMAIN1, PROMPT_DOMAIN2_SQ12, PROMPT_DOMAIN5

    assert "central randomization infrastructure" not in PROMPT_DOMAIN1
    assert "direct evidence that a random method was used" not in PROMPT_DOMAIN1
    assert "Masking = DOUBLE or QUADRUPLE supports N or PN" not in PROMPT_DOMAIN2_SQ12
    assert "analysis plan was pre-specified" not in PROMPT_DOMAIN5
    assert "endpoints were specified in the registry" not in PROMPT_DOMAIN5


def test_prompt_domain3_accepts_ctgov_flow():
    from rob2_pipeline.prompts import PROMPT_DOMAIN3

    result = PROMPT_DOMAIN3.format(
        intervention="Docetaxel + ADT",
        comparator="ADT alone",
        outcome="Overall Survival",
        n_randomized="790",
        consort_text="",
        missing_data_text="",
        sensitivity_text="",
        rag_text="",
        ctgov_flow="Participant flow:\n  STARTED: ADT + Docetaxel: 397, ADT Alone: 393",
    )

    assert "397" in result


def test_prompt_domain5_accepts_ctgov_description():
    from rob2_pipeline.prompts import PROMPT_DOMAIN5

    result = PROMPT_DOMAIN5.format(
        intervention="Docetaxel + ADT",
        comparator="ADT alone",
        outcome="Overall Survival",
        outcome_type="vital-status",
        numerical_result="HR 0.61",
        registration_number="NCT00309985",
        registered_endpoint="Overall Survival",
        registered_secondary_endpoints="Time to CRPC",
        reported_endpoint="Overall Survival",
        ctgov_outcomes="PRIMARY: Overall Survival",
        ctgov_description="Authoritative ClinicalTrials.gov registry description:\nPRIMARY OBJECTIVE: Overall survival.",
        registration_text="",
        sap_text="",
        results_text="",
        rag_text="",
    )

    assert "PRIMARY OBJECTIVE" in result


def test_domain_prompts_label_primary_evidence_and_retrieved_context():
    from rob2_pipeline.prompts import PROMPT_DOMAIN1

    result = PROMPT_DOMAIN1.format(
        intervention="Docetaxel + ADT",
        comparator="ADT alone",
        outcome="Overall Survival",
        randomization_text="Central allocation by statistical center.",
        baseline_text="Groups were balanced.",
        consort_text="All participants accounted for.",
        rag_text="Generic randomized trial sentence.",
        ctgov_design="",
    )

    assert "PRIMARY EVIDENCE" in result
    assert "ADDITIONAL RETRIEVED CONTEXT" in result
    assert "Central allocation by statistical center." in result
    assert "Generic randomized trial sentence." in result


def test_domain1_prompt_guides_stratified_cooperative_group_concealment_inference():
    from rob2_pipeline.prompts import PROMPT_DOMAIN1

    assert "stratified randomization" in PROMPT_DOMAIN1
    assert "PY rather than NI for Q1.2" in PROMPT_DOMAIN1


def test_domain4_prompt_guides_outcome_specific_q44_reasoning():
    from rob2_pipeline.prompts import PROMPT_DOMAIN4

    result = PROMPT_DOMAIN4.format(
        intervention="Docetaxel + ADT",
        comparator="ADT alone",
        outcome="Progression-Free Survival",
        outcome_type="clinician-composite",
        sq_2_1="Y",
        outcome_measurement_text=(
            "Overall survival was defined as time from randomization to death. "
            "Progression-free survival was biochemical, symptomatic, or radiographic progression."
        ),
        blinding_text="Open-label trial.",
        rag_text="",
    )

    assert "definitions for multiple outcomes" in result
    assert "based only on the definition for Progression-Free Survival" in result
    assert "outcomes involving judgment" in result
    assert "all-cause mortality" in result
    assert "mechanical" in result


def test_preliminary_prompt_excludes_composites_from_vital_status():
    from rob2_pipeline.prompts import PROMPT_PRELIMINARY_INFO

    assert "death is the only event that counts" in PROMPT_PRELIMINARY_INFO
    assert "Do not use this category for composite endpoints" in PROMPT_PRELIMINARY_INFO
    assert "Event-free survival combining death" in PROMPT_PRELIMINARY_INFO
    assert "participant questionnaire" in PROMPT_PRELIMINARY_INFO
    assert "PFS" not in PROMPT_PRELIMINARY_INFO
    assert "CRPC" not in PROMPT_PRELIMINARY_INFO


def test_domain2_conditional_prompt_calibrates_q23_to_trial_context():
    from rob2_pipeline.prompts import PROMPT_DOMAIN2_CONDITIONAL

    assert "NI is a last resort" in PROMPT_DOMAIN2_CONDITIONAL
    assert "recruitment, engagement, unblinding, or trial personnel" in PROMPT_DOMAIN2_CONDITIONAL
    assert "consistent with what could occur outside the trial context" in PROMPT_DOMAIN2_CONDITIONAL
    assert "protocol-consistent changes" in PROMPT_DOMAIN2_CONDITIONAL
    assert "pre-treatment non-starts" not in PROMPT_DOMAIN2_CONDITIONAL
    assert "external change in standard of care" not in PROMPT_DOMAIN2_CONDITIONAL


def test_domain3_prompt_includes_general_time_to_event_censoring_guidance():
    from rob2_pipeline.prompts import PROMPT_DOMAIN3

    assert "time-to-event analyses" in PROMPT_DOMAIN3
    assert "participants' follow-up is censored when they stop or change their assigned intervention" in PROMPT_DOMAIN3
    assert "rates of censoring differ between intervention groups" in PROMPT_DOMAIN3
    assert "switching to second-line therapy is itself an outcome-related event" not in PROMPT_DOMAIN3


def test_domain4_prompt_infers_assessor_awareness_in_open_label_trials():
    from rob2_pipeline.prompts import PROMPT_DOMAIN4

    result = PROMPT_DOMAIN4.format(
        intervention="Docetaxel + ADT",
        comparator="ADT alone",
        outcome="Progression-Free Survival",
        outcome_type="clinician-composite",
        sq_2_1="Y",
        outcome_measurement_text="Progression was investigator-assessed.",
        blinding_text="Open-label trial.",
        rag_text="",
    )

    assert "If the trial is open-label (Q2.1=Y" in result
    assert "answer PY (assessors likely aware of assignment) rather than NI" in result
    assert "cannot be inferred from any available evidence" in result


def test_domain4_prompt_restricts_q44_objective_rule_to_vital_status():
    from rob2_pipeline.prompts import PROMPT_DOMAIN4

    assert "observer-reported outcomes involving judgment" in PROMPT_DOMAIN4
    assert "observer-reported outcomes that do not involve judgment" in PROMPT_DOMAIN4
    assert "centrally blinded" in PROMPT_DOMAIN4
    assert "PFS" not in PROMPT_DOMAIN4
    assert "TTP" not in PROMPT_DOMAIN4
    assert "CRPC" not in PROMPT_DOMAIN4


def test_domain4_prompt_calibrates_q45_some_concerns_vs_high():
    from rob2_pipeline.prompts import PROMPT_DOMAIN4

    assert "could have been influenced" in PROMPT_DOMAIN4
    assert "likely was influenced" in PROMPT_DOMAIN4
    assert "patient-reported symptoms in trials of homeopathy" in PROMPT_DOMAIN4
    assert "standardized outcome criteria" in PROMPT_DOMAIN4
    assert "open-label oncology" not in PROMPT_DOMAIN4


def test_domain5_prompt_clarifies_composite_endpoints_are_not_selective_measurements():
    from rob2_pipeline.prompts import PROMPT_DOMAIN5

    result = PROMPT_DOMAIN5.format(
        intervention="Docetaxel + ADT",
        comparator="ADT alone",
        outcome="Progression-Free Survival",
        outcome_type="clinician-composite",
        numerical_result="HR 0.61",
        registration_number="NCT00309985",
        registered_endpoint="Progression-Free Survival",
        registered_secondary_endpoints="Progression-Free Survival",
        reported_endpoint="Progression-Free Survival",
        ctgov_outcomes="SECONDARY: Progression-Free Survival",
        ctgov_description="",
        registration_text="",
        sap_text="",
        results_text="",
        rag_text="",
    )

    assert "A pre-specified composite endpoint" in result
    assert "is NOT multiple eligible outcome measurements" in result
    assert "Answer Q5.2=N" in result
