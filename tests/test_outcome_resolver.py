from rob2_pipeline.nodes.outcome_resolver import (
    infer_outcome_properties,
    outcome_type_from_properties,
)


def test_mortality_endpoint_is_vital_status():
    props = infer_outcome_properties(
        "All-cause mortality",
        "The endpoint was death from any cause.",
    )

    assert props["objective_event"] is True
    assert props["composite"] is False
    assert outcome_type_from_properties(props) == "vital-status"


def test_composite_time_to_event_is_not_vital_status():
    props = infer_outcome_properties(
        "Event-free survival",
        "Event-free survival was time to relapse, hospitalization, treatment failure, or death.",
    )

    assert props["time_to_event"] is True
    assert props["composite"] is True
    assert outcome_type_from_properties(props) == "clinician-composite"


def test_patient_reported_outcome_takes_priority():
    props = infer_outcome_properties(
        "Pain severity",
        "Pain severity was self-reported using a questionnaire.",
    )

    assert props["patient_reported"] is True
    assert outcome_type_from_properties(props) == "patient-reported"


def test_safety_harm_outcome_is_clinician_graded():
    props = infer_outcome_properties(
        "Serious harms",
        "Serious adverse events and toxicity were graded by study clinicians.",
    )

    assert props["safety_harm"] is True
    assert outcome_type_from_properties(props) == "clinician-graded"


def test_lab_threshold_outcome_is_biomarker_when_not_composite():
    props = infer_outcome_properties(
        "Viral suppression",
        "Viral suppression was measured by laboratory assay below a prespecified threshold.",
    )

    assert props["lab_or_imaging_threshold"] is True
    assert outcome_type_from_properties(props) == "biomarker"
