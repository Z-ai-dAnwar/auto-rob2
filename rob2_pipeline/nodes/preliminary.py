import re

from lxml import etree

from rob2_pipeline.nodes.common import call_node_llm
from rob2_pipeline.prompts import PROMPT_PRELIMINARY_INFO
from rob2_pipeline.state import RoB2State
from rob2_pipeline.xml_parser import extract_tag


def _nested_text(xml_string: str, parent: str, child: str, default: str = "Not reported") -> str:
    try:
        parser = etree.XMLParser(recover=True)
        root = etree.fromstring(f"<root>{xml_string}</root>".encode(), parser=parser)
        value = root.findtext(f".//{parent}/{child}")
        return value.strip() if value and value.strip() else default
    except Exception:
        return default


def _first_match(text: str, patterns: list[str], default: str = "Not reported") -> str:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return default


def _prefer_extracted(value: str, fallback: str) -> str:
    return fallback if value == "Not reported" and fallback != "Not reported" else value


def preliminary_info_node(state: RoB2State) -> RoB2State:
    sections = state["sections"]
    prompt = PROMPT_PRELIMINARY_INFO.format(
        abstract_text=sections.get("abstract", ""),
        methods_text=sections.get("methods", ""),
        results_text=sections.get("results", ""),
        registration_text=sections.get("registration", ""),
        consort_text=sections.get("consort", ""),
    )
    response, log, _ = call_node_llm(state, prompt, "preliminary_info")
    requested_outcome = state.get("outcome", "")
    extracted_outcome = _nested_text(response, "outcome_assessed", "value")
    evidence_text = "\n".join([state.get("full_text", ""), *sections.values()])
    registration_number = _prefer_extracted(
        _nested_text(response, "trial_registration", "number"),
        _first_match(evidence_text, [r"\b(NCT\d{8})\b", r"\b(ISRCTN\d+)\b"]),
    )
    n_randomized = _prefer_extracted(
        _nested_text(response, "n_randomized", "value"),
        _first_match(evidence_text, [r"(\d{2,6})\s+(?:patients|participants)\s+(?:were\s+)?randomi[sz]ed"]),
    )
    registered_analysis = _prefer_extracted(
        _nested_text(response, "registered_analysis", "value"),
        "ITT" if re.search(r"intention[- ]to[- ]treat|\bITT\b", evidence_text, flags=re.IGNORECASE) else "Not reported",
    )
    return {
        "intervention": _nested_text(response, "experimental_intervention", "value"),
        "comparator": _nested_text(response, "comparator_intervention", "value"),
        "outcome": requested_outcome or extracted_outcome,
        "outcome_type": (extract_tag(response, "outcome_type") or "objective").strip(),
        "numerical_result": _nested_text(response, "numerical_result", "value"),
        "effect_of_interest": state.get("effect_of_interest", "ITT"),
        "registration_number": registration_number,
        "n_randomized": n_randomized,
        "registered_endpoint": _nested_text(response, "registered_primary_endpoint", "value"),
        "registered_analysis": registered_analysis,
        "sources_consulted": [name for name, text in sections.items() if text],
        "llm_call_log": log,
    }
