import re

from rob2_pipeline.models import EVIDENCE_SECTION_FIELDS, format_evidence
from rob2_pipeline.state import RoB2State
from rob2_pipeline.state_factory import DEFAULT_OUTCOME_PROPERTIES


_PATTERNS = {
    "patient_reported": re.compile(
        r"\b(patient[- ]reported|self[- ]reported|questionnaire|quality of life|pain score|symptom score)\b",
        re.I,
    ),
    "safety_harm": re.compile(
        r"\b(adverse event|serious adverse|toxicity|harm|side effect|safety|tolerability)\b",
        re.I,
    ),
    "time_to_event": re.compile(
        r"\b(time to|survival|hazard ratio|kaplan[- ]meier|censor|event[- ]free)\b",
        re.I,
    ),
    "death_only": re.compile(
        r"\b(overall survival|all[- ]cause mortality|death from any cause|mortality|vital status)\b",
        re.I,
    ),
    "composite": re.compile(
        r"\b(composite|progression|relapse|recurrence|hospitali[sz]ation|treatment failure|event[- ]free|or death)\b",
        re.I,
    ),
    "lab_or_imaging": re.compile(
        r"\b(biomarker|laboratory|lab |blood|serum|imaging|radiographic|mri|ct scan|recist|threshold|assay)\b",
        re.I,
    ),
    "blinded_adjudication": re.compile(
        r"\b(blinded|masked|independent|central).{0,80}\b(adjudication|committee|review|assessor)\b",
        re.I,
    ),
}


def _evidence_text(state: RoB2State) -> str:
    evidence = state.get("evidence", {})
    parts = [state.get("outcome", ""), state.get("numerical_result", "")]
    for field in EVIDENCE_SECTION_FIELDS:
        section = evidence.get(field) if evidence else None
        if section:
            parts.append(format_evidence(section))
    return "\n\n".join(part for part in parts if part)


def _death_is_sole_event(text: str) -> bool:
    if not _PATTERNS["death_only"].search(text):
        return False
    outcome_window = text[:1200]
    return not re.search(
        r"\b(progression|relapse|recurrence|hospitali[sz]ation|treatment failure|composite|or death)\b",
        outcome_window,
        re.I,
    )


def infer_outcome_properties(outcome: str, evidence_text: str) -> dict[str, bool]:
    text = "\n".join([outcome, evidence_text])
    props = dict(DEFAULT_OUTCOME_PROPERTIES)
    props["patient_reported"] = bool(_PATTERNS["patient_reported"].search(text))
    props["safety_harm"] = bool(_PATTERNS["safety_harm"].search(text))
    props["time_to_event"] = bool(_PATTERNS["time_to_event"].search(text))
    props["composite"] = bool(
        _PATTERNS["composite"].search(text)
    ) and not _death_is_sole_event(text)
    props["lab_or_imaging_threshold"] = bool(_PATTERNS["lab_or_imaging"].search(text))
    props["blinded_adjudication"] = bool(_PATTERNS["blinded_adjudication"].search(text))
    props["objective_event"] = _death_is_sole_event(text) or (
        props["lab_or_imaging_threshold"]
        and not props["patient_reported"]
        and not props["composite"]
    )
    props["clinician_judged"] = (
        not props["patient_reported"] and not props["objective_event"]
    )
    if props["safety_harm"]:
        props["clinician_judged"] = True
    return props


def outcome_type_from_properties(props: dict[str, bool]) -> str:
    if props.get("patient_reported"):
        return "patient-reported"
    if props.get("safety_harm"):
        return "clinician-graded"
    if props.get("lab_or_imaging_threshold") and not props.get("composite"):
        return "biomarker"
    if props.get("objective_event") and not props.get("composite"):
        return "vital-status"
    return "clinician-composite"


def outcome_resolver_node(state: RoB2State) -> RoB2State:
    text = _evidence_text(state)
    props = infer_outcome_properties(state.get("outcome", ""), text)
    resolved_type = outcome_type_from_properties(props)
    errors = list(state.get("errors", []))
    previous_type = state.get("outcome_type", "")
    if previous_type and previous_type != resolved_type:
        errors.append(
            "INFO: outcome_type normalized from "
            f"{previous_type!r} to {resolved_type!r} using generic outcome-property inference."
        )
    return {
        "outcome_properties": props,
        "outcome_type": resolved_type,
        "errors": errors,
    }
