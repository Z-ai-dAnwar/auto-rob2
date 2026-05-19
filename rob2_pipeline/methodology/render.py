from rob2_pipeline.methodology.types import DomainMethodology


def render_methodology(methodology: DomainMethodology, sq_ids: list[str]) -> str:
    lines = [
        "=== CANONICAL RoB 2 METHODOLOGY ===",
        f"{methodology.domain_id}: {methodology.title}",
    ]
    if methodology.principles:
        lines.append("Principles:")
        lines.extend(f"- {principle}" for principle in methodology.principles)

    for sq_id in sq_ids:
        if sq_id not in methodology.rule_cards:
            raise KeyError(f"Missing rule card for {methodology.domain_id} SQ {sq_id}")
        card = methodology.rule_cards[sq_id]
        lines.extend(["", f"SQ {card.sq_id}: {card.question}"])
        if card.applicability:
            lines.append(f"Applicability: {card.applicability}")
        for option, rule in card.response_rules.items():
            lines.append(f"- {option}: {rule.guidance}")
        if card.algorithm_note:
            lines.append(f"Algorithm note: {card.algorithm_note}")
        for note in card.notes:
            lines.append(f"Note: {note}")
        citations = "; ".join(citation.format() for citation in card.citations)
        lines.append(f"Citations: {citations}")

    return "\n".join(lines)
