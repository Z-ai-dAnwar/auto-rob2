import json
from pathlib import Path

from rob2_pipeline.constants import DEFAULT_EFFECT_OF_INTEREST
from rob2_pipeline.graph import build_rob2_graph
from rob2_pipeline.state import RoB2State
from rob2_pipeline.state_factory import create_initial_state


def run_assessment(
    pdf_path: str,
    outcome: str | None = None,
    effect_of_interest: str = DEFAULT_EFFECT_OF_INTEREST,
    output_dir: str = "outputs/",
) -> RoB2State:
    """
    Main entry point. Returns the completed state dict.
    Also writes: {output_dir}/{pdf_basename}_rob2_report.md
                 {output_dir}/{pdf_basename}_rob2_data.json
    """
    graph = build_rob2_graph()
    state = graph.invoke(create_initial_state(pdf_path, outcome, effect_of_interest))

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
