from lxml import etree

from rob2_pipeline.nodes.common import call_node_llm
from rob2_pipeline.prompts import PROMPT_PRELIMINARY_INFO
from rob2_pipeline.state import RoB2State
from rob2_pipeline.xml_parser import extract_tag


def _nested_text(xml_string: str, parent: str, child: str, default: str = "Not reported") -> str:
    try:
        root = etree.fromstring(f"<root>{xml_string}</root>".encode())
        value = root.findtext(f".//{parent}/{child}")
        return value.strip() if value and value.strip() else default
    except Exception:
        return default


def preliminary_info_node(state: RoB2State) -> RoB2State:
    sections = state["sections"]
    prompt = PROMPT_PRELIMINARY_INFO.format(
        abstract_text=sections.get("abstract", ""),
        methods_text=sections.get("methods", ""),
        results_text=sections.get("results", ""),
    )
    response, log = call_node_llm(state, prompt, "preliminary_info")
    requested_outcome = state.get("outcome", "")
    extracted_outcome = _nested_text(response, "outcome_assessed", "value")
    return {
        **state,
        "intervention": _nested_text(response, "experimental_intervention", "value"),
        "comparator": _nested_text(response, "comparator_intervention", "value"),
        "outcome": requested_outcome or extracted_outcome,
        "outcome_type": (extract_tag(response, "outcome_type") or "objective").strip(),
        "numerical_result": _nested_text(response, "numerical_result", "value"),
        "effect_of_interest": state.get("effect_of_interest", "ITT"),
        "registration_number": _nested_text(response, "trial_registration", "number"),
        "n_randomized": _nested_text(response, "n_randomized", "value"),
        "sources_consulted": [name for name, text in sections.items() if text],
        "llm_call_log": log,
    }
