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
    assert "Hard endpoints" in result
    assert "Composite endpoints or investigator-assessed endpoints" in result
    assert "Q4.4=PY" in result


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
