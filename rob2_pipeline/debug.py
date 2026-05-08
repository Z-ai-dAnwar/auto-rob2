from rob2_pipeline.state import RoB2State


def summarize_state(state: RoB2State) -> dict:
    """Return a compact debug summary for a completed run."""
    return {
        "is_rct": state.get("is_rct"),
        "overall_judgment": state.get("overall_judgment"),
        "human_review_priority": state.get("human_review_priority"),
        "ni_count": state.get("ni_count"),
        "domains": state.get("domain_judgments", {}),
        "errors_count": len(state.get("errors", [])),
        "llm_calls": len(state.get("llm_call_log", [])),
    }
