import pytest

from rob2_pipeline.judges import (
    judge_domain1,
    judge_domain2,
    judge_domain3,
    judge_domain4,
    judge_domain5,
    judge_overall,
)
from rob2_pipeline.nodes.domain3 import domain3_judge_node
from rob2_pipeline.nodes.domain4 import domain4_judge_node
from rob2_pipeline.nodes.domain5 import domain5_judge_node
from rob2_pipeline.prompts import PROMPT_DOMAIN2_ADHERING_ANALYSIS, PROMPT_DOMAIN2_ADHERING_CONDITIONAL, PROMPT_DOMAIN5


def sq(**answers):
    return {key: {"answer": value} for key, value in answers.items()}


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        (sq(**{"1.1": "Y", "1.2": "Y", "1.3": "N"}), "Low"),
        (sq(**{"1.1": "Y", "1.2": "Y", "1.3": "Y"}), "Some concerns"),
        (sq(**{"1.1": "N", "1.2": "Y", "1.3": "PY"}), "Some concerns"),
        (sq(**{"1.1": "Y", "1.2": "NI", "1.3": "PN"}), "Some concerns"),
        (sq(**{"1.1": "Y", "1.2": "NI", "1.3": "Y"}), "High"),
        (sq(**{"1.1": "Y", "1.2": "PN", "1.3": "N"}), "High"),
        ({}, "Some concerns"),
    ],
)
def test_judge_domain1(answers, expected):
    assert judge_domain1(answers)[0] == expected


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        (sq(**{"2.1": "N", "2.2": "PN", "2.6": "Y"}), "Low"),
        (sq(**{"2.1": "Y", "2.2": "N", "2.6": "Y"}), "Some concerns"),
        (sq(**{"2.1": "Y", "2.2": "NI", "2.6": "Y"}), "Some concerns"),
        (sq(**{"2.1": "Y", "2.2": "Y", "2.3": "N", "2.6": "Y"}), "Low"),
        (sq(**{"2.1": "Y", "2.2": "Y", "2.3": "Y", "2.4": "Y", "2.5": "PY", "2.6": "Y"}), "Some concerns"),
        (sq(**{"2.1": "Y", "2.2": "Y", "2.3": "NI", "2.6": "Y"}), "Some concerns"),
        (sq(**{"2.1": "Y", "2.2": "Y", "2.3": "Y", "2.4": "Y", "2.5": "Y", "2.6": "Y"}), "Some concerns"),
        (sq(**{"2.1": "Y", "2.2": "Y", "2.3": "Y", "2.4": "Y", "2.5": "N", "2.6": "N", "2.7": "Y"}), "High"),
        (sq(**{"2.1": "Y", "2.2": "Y", "2.3": "Y", "2.4": "N", "2.5": "N", "2.6": "Y"}), "Some concerns"),
        (sq(**{"2.1": "N", "2.2": "N", "2.6": "N", "2.7": "N"}), "Some concerns"),
        (sq(**{"2.1": "N", "2.2": "N", "2.6": "N", "2.7": "Y"}), "High"),
        (sq(**{"2.1": "NI", "2.2": "NI", "2.3": "NI", "2.4": "NI", "2.5": "NI", "2.6": "NI", "2.7": "NI"}), "High"),
        ({}, "Some concerns"),
        (sq(**{"2.1": "NA", "2.2": "NA", "2.3": "NA", "2.4": "NA", "2.5": "NA", "2.6": "NA", "2.7": "NA"}), "Some concerns"),
    ],
)
def test_judge_domain2(answers, expected):
    assert judge_domain2(answers)[0] == expected


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        (sq(**{"2.1": "N", "2.2": "N", "2.3": "NA", "2.4": "N", "2.5": "N", "2.6": "NA"}), "Low"),
        (sq(**{"2.1": "Y", "2.2": "Y", "2.3": "Y", "2.4": "N", "2.5": "N", "2.6": "NA"}), "Low"),
        (sq(**{"2.1": "Y", "2.2": "Y", "2.3": "N", "2.4": "N", "2.5": "N", "2.6": "Y"}), "Some concerns"),
        (sq(**{"2.1": "N", "2.2": "N", "2.3": "NA", "2.4": "Y", "2.5": "N", "2.6": "Y"}), "Some concerns"),
        (sq(**{"2.1": "N", "2.2": "N", "2.3": "NA", "2.4": "N", "2.5": "Y", "2.6": "N"}), "High"),
        (sq(**{"2.1": "Y", "2.2": "Y", "2.3": "NI", "2.4": "N", "2.5": "N", "2.6": "NI"}), "High"),
    ],
)
def test_judge_domain2_per_protocol(answers, expected):
    assert judge_domain2(answers, "per-protocol")[0] == expected


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        (sq(**{"3.1": "Y"}), "Low"),
        (sq(**{"3.1": "N", "3.2": "Y"}), "Low"),
        (sq(**{"3.1": "N", "3.2": "N", "3.3": "N"}), "Low"),
        (sq(**{"3.1": "N", "3.2": "N", "3.3": "Y", "3.4": "N"}), "Some concerns"),
        (sq(**{"3.1": "N", "3.2": "N", "3.3": "Y", "3.4": "Y"}), "High"),
        (sq(**{"3.1": "NI", "3.2": "N", "3.3": "NI", "3.4": "NI"}), "High"),
        ({}, "Some concerns"),
        (sq(**{"3.1": "NA", "3.2": "NA", "3.3": "NA", "3.4": "NA"}), "Some concerns"),
    ],
)
def test_judge_domain3(answers, expected):
    assert judge_domain3(answers)[0] == expected


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        (sq(**{"4.1": "N", "4.2": "N", "4.3": "N"}), "Low"),
        (sq(**{"4.1": "N", "4.2": "N", "4.3": "Y", "4.4": "N"}), "Low"),
        (sq(**{"4.1": "N", "4.2": "N", "4.3": "Y", "4.4": "N", "4.5": "NA"}), "Low"),
        (sq(**{"4.1": "N", "4.2": "N", "4.3": "Y", "4.4": "Y", "4.5": "N"}), "Some concerns"),
        (sq(**{"4.1": "N", "4.2": "N", "4.3": "Y", "4.4": "PY", "4.5": "N"}), "Some concerns"),
        (sq(**{"4.1": "N", "4.2": "N", "4.3": "Y", "4.4": "PY", "4.5": "PN"}), "Some concerns"),
        (sq(**{"4.1": "N", "4.2": "N", "4.3": "Y", "4.4": "PY", "4.5": "NI"}), "High"),
        (sq(**{"4.1": "N", "4.2": "N", "4.3": "Y", "4.4": "Y", "4.5": "Y"}), "High"),
        (sq(**{"4.1": "N", "4.2": "NI", "4.3": "N"}), "Some concerns"),
        (sq(**{"4.1": "N", "4.2": "NI", "4.3": "Y", "4.4": "N"}), "Some concerns"),
        (sq(**{"4.1": "N", "4.2": "NI", "4.3": "Y", "4.4": "Y", "4.5": "N"}), "Some concerns"),
        (sq(**{"4.1": "N", "4.2": "NI", "4.3": "Y", "4.4": "Y", "4.5": "Y"}), "High"),
        (sq(**{"4.1": "Y", "4.2": "N"}), "High"),
        (sq(**{"4.1": "N", "4.2": "Y"}), "High"),
        (sq(**{"4.1": "NI", "4.2": "NI", "4.3": "NI", "4.4": "NI", "4.5": "NI"}), "High"),
        ({}, "Some concerns"),
        (sq(**{"4.1": "NA", "4.2": "NA", "4.3": "NA", "4.4": "NA", "4.5": "NA"}), "Some concerns"),
    ],
)
def test_judge_domain4(answers, expected):
    assert judge_domain4(answers)[0] == expected


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        (sq(**{"5.1": "Y", "5.2": "N", "5.3": "N"}), "Low"),
        (sq(**{"5.1": "N", "5.2": "N", "5.3": "N"}), "Some concerns"),
        (sq(**{"5.1": "Y", "5.2": "N", "5.3": "NI"}), "Some concerns"),
        (sq(**{"5.1": "Y", "5.2": "NI", "5.3": "N"}), "Some concerns"),
        (sq(**{"5.1": "Y", "5.2": "NI", "5.3": "NI"}), "Some concerns"),
        (sq(**{"5.1": "Y", "5.2": "Y", "5.3": "N"}), "High"),
        (sq(**{"5.1": "Y", "5.2": "N", "5.3": "PY"}), "High"),
        ({}, "Some concerns"),
        (sq(**{"5.1": "NA", "5.2": "NA", "5.3": "NA"}), "Some concerns"),
    ],
)
def test_judge_domain5(answers, expected):
    assert judge_domain5(answers)[0] == expected


@pytest.mark.parametrize(
    ("domains", "expected", "rationale_part"),
    [
        ({"D1": "Low", "D2": "Low", "D3": "Low", "D4": "Low", "D5": "Low"}, "Low", "Low in all"),
        ({"D1": "Low", "D2": "Some concerns", "D3": "Low", "D4": "Low", "D5": "Low"}, "Some concerns", "1 domain"),
        ({"D1": "Some concerns", "D2": "Some concerns", "D3": "Low", "D4": "Low", "D5": "Low"}, "Some concerns", "2 domains with Some concerns"),
        ({"D1": "Some concerns", "D2": "Some concerns", "D3": "Some concerns", "D4": "Low", "D5": "Low"}, "Some concerns", "substantially lower confidence"),
        ({"D1": "Low", "D2": "High", "D3": "Low", "D4": "Low", "D5": "Low"}, "High", "D2"),
    ],
)
def test_judge_overall(domains, expected, rationale_part):
    judgment, rationale = judge_overall(domains)
    assert judgment == expected
    assert rationale_part in rationale


def test_domain_nodes_do_not_override_algorithm_by_outcome_label():
    d3_state = {
        "outcome": "Progression-Free Survival",
        "sq_answers": sq(**{"3.1": "Y"}),
        "domain_judgments": {},
        "domain_rationales": {},
    }
    assert domain3_judge_node(d3_state)["domain_judgments"]["D3"] == "Low"

    d4_state = {
        "outcome": "Progression-Free Survival",
        "sq_answers": sq(**{"2.1": "Y", "4.1": "N", "4.2": "N", "4.3": "N"}),
        "domain_judgments": {},
        "domain_rationales": {},
    }
    assert domain4_judge_node(d4_state)["domain_judgments"]["D4"] == "Low"

    d5_state = {
        "outcome": "Progression-Free Survival",
        "registration_number": "NCT00000000",
        "sq_answers": sq(**{"5.1": "NI", "5.2": "N", "5.3": "N"}),
        "domain_judgments": {},
        "domain_rationales": {},
    }
    assert domain5_judge_node(d5_state)["domain_judgments"]["D5"] == "Some concerns"


def test_prompts_include_skill_domain2_and_domain5_guidance():
    assert "effect of adhering to intervention" in PROMPT_DOMAIN2_ADHERING_CONDITIONAL
    assert "instrumental variable" in PROMPT_DOMAIN2_ADHERING_ANALYSIS
    assert "selected, on the basis of the results" in PROMPT_DOMAIN5
