import pytest

from rob2_pipeline.xml_parser import extract_tag, parse_sq_response, validate_sq_answers


def test_extract_tag_well_formed_fragment():
    assert extract_tag("<screening><is_rct>YES</is_rct></screening>", "is_rct") == "YES"


def test_parse_sq_response_valid_xml():
    xml = """
    <domain1>
      <sq_1_1>
        <answer>Y</answer>
        <quote>"Computer-generated sequence" (Methods)</quote>
        <justification>Random method was stated.</justification>
      </sq_1_1>
      <sq_1_2>
        <answer>PY</answer>
        <quote>"Central allocation" (Methods)</quote>
        <justification>Central allocation implies concealment.</justification>
        <uncertainty_flag>normal</uncertainty_flag>
      </sq_1_2>
    </domain1>
    """

    parsed = parse_sq_response(xml, ["1.1", "1.2"])

    assert parsed["1.1"]["answer"] == "Y"
    assert parsed["1.1"]["quote"] == '"Computer-generated sequence" (Methods)'
    assert parsed["1.2"]["answer"] == "PY"
    assert parsed["1.2"]["uncertainty_flag"] == "NORMAL"


def test_parse_sq_response_malformed_xml_raises():
    xml = """
    <domain1>
      <sq_1_1>
        <answer>Probably Yes</answer>
        <quote>"Randomized centrally" (Methods)</quote>
        <justification>Supports a probably yes answer.</justification>
    """

    with pytest.raises(Exception):
        parse_sq_response(xml, ["1.1"])


def test_parse_sq_response_missing_sq_raises():
    xml = """
    <domain1>
      <sq_1_1>
        <answer>Y</answer>
        <quote>"Randomized" (Abstract)</quote>
        <justification>States randomized.</justification>
      </sq_1_1>
    </domain1>
    """

    with pytest.raises(ValueError, match="Missing signaling question"):
        parse_sq_response(xml, ["1.1", "1.2"])


def test_parse_sq_response_unexpected_answer_values_raise():
    xml = """
    <domain5>
      <sq_5_1>
        <answer>Definitely</answer>
        <quote></quote>
        <justification></justification>
      </sq_5_1>
      <sq_5_2>
        <answer>Not applicable</answer>
      </sq_5_2>
    </domain5>
    """

    with pytest.raises(ValueError, match="Invalid signaling-question answer"):
        parse_sq_response(xml, ["5.1", "5.2"])


def test_parse_sq_response_strips_xml_code_fences():
    xml = """
    ```xml
    <domain1>
      <sq_1_1>
        <answer>Y</answer>
        <quote>\"Randomized\" (Methods)</quote>
        <justification>Directly reported.</justification>
      </sq_1_1>
    </domain1>
    ```
    """
    parsed = parse_sq_response(xml, ["1.1"])
    assert parsed["1.1"]["answer"] == "Y"


def test_validate_sq_answers_flags_suspected_parse_failures():
    parsed = {
        "1.1": {"answer": "NI", "justification": "No relevant text found"},
        "1.2": {"answer": "Y", "justification": "Found explicit method"},
    }
    suspected = validate_sq_answers(parsed, ["1.1", "1.2"])
    assert suspected == ["1.1"]
