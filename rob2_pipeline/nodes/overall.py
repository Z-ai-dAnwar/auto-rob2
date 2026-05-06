from rob2_pipeline.judges.overall import judge_overall
from rob2_pipeline.state import RoB2State


def overall_judge_node(state: RoB2State) -> RoB2State:
    judgment, rationale = judge_overall(state.get("domain_judgments", {}))
    sq_answers = state.get("sq_answers", {})
    ni_count = sum(1 for answer in sq_answers.values() if answer.get("answer") == "NI")
    high_uncertainty_sqs = [
        sq_id for sq_id, answer in sq_answers.items() if answer.get("uncertainty_flag") == "HIGH"
    ]
    if judgment == "High" or high_uncertainty_sqs or ni_count >= 5:
        priority = "HIGH"
    elif judgment == "Some concerns" or ni_count >= 2:
        priority = "MEDIUM"
    else:
        priority = "LOW"
    return {
        **state,
        "overall_judgment": judgment,
        "overall_rationale": rationale,
        "ni_count": ni_count,
        "high_uncertainty_sqs": high_uncertainty_sqs,
        "human_review_priority": priority,
    }
