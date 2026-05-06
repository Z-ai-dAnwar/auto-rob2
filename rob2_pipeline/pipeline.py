import json
from pathlib import Path

from rob2_pipeline.graph import build_rob2_graph


def _initial_state(pdf_path: str, outcome: str | None, effect_of_interest: str) -> dict:
    return {
        "pdf_path": pdf_path,
        "full_text": "",
        "sections": {},
        "is_rct": False,
        "rct_screen_evidence": "",
        "intervention": "Not reported",
        "comparator": "Not reported",
        "outcome": outcome or "",
        "outcome_type": "objective",
        "numerical_result": "Not reported",
        "effect_of_interest": effect_of_interest,
        "registration_number": "Not reported",
        "n_randomized": "Not reported",
        "sources_consulted": [],
        "sq_answers": {},
        "domain_judgments": {},
        "domain_rationales": {},
        "overall_judgment": "",
        "overall_rationale": "",
        "ni_count": 0,
        "high_uncertainty_sqs": [],
        "human_review_priority": "HIGH",
        "markdown_report": "",
        "json_output": {},
        "errors": [],
        "llm_call_log": [],
    }


def run_assessment(
    pdf_path: str,
    outcome: str | None = None,
    effect_of_interest: str = "ITT",
    output_dir: str = "outputs/",
) -> dict:
    """
    Main entry point. Returns the completed state dict.
    Also writes: {output_dir}/{pdf_basename}_rob2_report.md
                 {output_dir}/{pdf_basename}_rob2_data.json
    """
    graph = build_rob2_graph()
    state = graph.invoke(_initial_state(pdf_path, outcome, effect_of_interest))

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    base = Path(pdf_path).stem

    if state.get("markdown_report"):
        (output_path / f"{base}_rob2_report.md").write_text(state["markdown_report"], encoding="utf-8")
    json_data = state.get("json_output") or dict(state)
    (output_path / f"{base}_rob2_data.json").write_text(
        json.dumps(json_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return state
