import pytest


EXPECTED_SQ_IDS = {
    "D1": {"1.1", "1.2", "1.3"},
    "D2_ASSIGNMENT": {"2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7"},
    "D2_ADHERING": {"2.1", "2.2", "2.3a", "2.4a", "2.5a", "2.6a"},
    "D3": {"3.1", "3.2", "3.3", "3.4"},
    "D4": {"4.1", "4.2", "4.3", "4.4", "4.5"},
    "D5": {"5.1", "5.2", "5.3"},
}


def test_rule_card_requires_citation_and_response_rules():
    from rob2_pipeline.methodology.types import Citation, ResponseRule, RuleCard

    card = RuleCard(
        sq_id="1.1",
        question="Was the allocation sequence random?",
        response_rules={
            "Y": ResponseRule("random component explicitly described"),
            "NI": ResponseRule("only states randomized with no useful detail"),
        },
        citations=[Citation("Sterne 2019 supplement", "p.1")],
    )

    assert card.sq_id == "1.1"
    assert "Y" in card.response_rules
    assert card.citations[0].label == "Sterne 2019 supplement"


def test_render_methodology_includes_sq_ids_options_and_citations():
    from rob2_pipeline.methodology.render import render_methodology
    from rob2_pipeline.methodology.types import (
        Citation,
        DomainMethodology,
        ResponseRule,
        RuleCard,
    )

    methodology = DomainMethodology(
        domain_id="D1",
        title="Bias arising from the randomization process",
        principles=["NI is reserved for insufficient detail."],
        rule_cards={
            "1.1": RuleCard(
                sq_id="1.1",
                question="Was the allocation sequence random?",
                response_rules={
                    "Y": ResponseRule("random component used"),
                    "NI": ResponseRule("insufficient detail"),
                },
                citations=[Citation("Sterne 2019 supplement", "p.1")],
            )
        },
    )

    rendered = render_methodology(methodology, ["1.1"])

    assert "CANONICAL RoB 2 METHODOLOGY" in rendered
    assert "SQ 1.1" in rendered
    assert "Y: random component used" in rendered
    assert "Sterne 2019 supplement p.1" in rendered


def test_render_methodology_rejects_missing_sq_id():
    from rob2_pipeline.methodology.render import render_methodology
    from rob2_pipeline.methodology.types import DomainMethodology

    methodology = DomainMethodology(
        domain_id="D1", title="Domain 1", principles=[], rule_cards={}
    )

    with pytest.raises(KeyError, match="Missing rule card"):
        render_methodology(methodology, ["1.1"])


def test_all_domain_methodologies_have_expected_rule_cards():
    from rob2_pipeline.methodology import METHODOLOGIES

    assert set(METHODOLOGIES) == set(EXPECTED_SQ_IDS)
    for key, expected_ids in EXPECTED_SQ_IDS.items():
        methodology = METHODOLOGIES[key]
        assert set(methodology.rule_cards) == expected_ids


def test_all_rule_cards_have_valid_options_and_citations():
    from rob2_pipeline.methodology import METHODOLOGIES
    from rob2_pipeline.methodology.types import VALID_RESPONSE_OPTIONS

    valid_options = set(VALID_RESPONSE_OPTIONS)
    for methodology in METHODOLOGIES.values():
        for card in methodology.rule_cards.values():
            assert card.question
            assert card.citations
            assert set(card.response_rules).issubset(valid_options)
            assert card.response_rules
