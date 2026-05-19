"""Tests for ClinicalTrials.gov API extraction functions."""

from rob2_pipeline.registration_api import (
    extract_description,
    extract_design_info,
    extract_participant_flow,
    format_description_for_prompt,
    format_design_for_prompt,
    format_flow_for_prompt,
)


SAMPLE_DATA = {
    "protocolSection": {
        "designModule": {
            "studyType": "INTERVENTIONAL",
            "phases": ["PHASE3"],
            "designInfo": {
                "allocationType": "RANDOMIZED",
                "interventionModel": "PARALLEL",
                "primaryPurpose": "TREATMENT",
                "maskingInfo": {"masking": "NONE", "whoMasked": []},
            },
            "enrollmentInfo": {"count": 790, "enrollmentType": "ACTUAL"},
        },
        "descriptionModule": {
            "briefSummary": "Phase III trial of ADT plus docetaxel vs ADT alone.",
            "detailedDescription": "PRIMARY OBJECTIVE: Overall survival.\nSECONDARY OBJECTIVE: Time to castration resistance.",
        },
        "oversightModule": {"oversightHasDmc": True},
        "sponsorCollaboratorsModule": {
            "leadSponsor": {
                "name": "ECOG-ACRIN Cancer Research Group",
                "class": "NETWORK",
            }
        },
        "outcomesModule": {
            "primaryOutcomes": [{"measure": "Overall Survival"}],
            "secondaryOutcomes": [{"measure": "Time to CRPC"}],
        },
    },
    "resultsSection": {
        "participantFlowModule": {
            "recruitmentDetails": "Study activated 2006; 790 accrued.",
            "groups": [
                {"id": "FG000", "title": "ADT + Docetaxel"},
                {"id": "FG001", "title": "ADT Alone"},
            ],
            "periods": [
                {
                    "title": "Overall Study",
                    "milestones": [
                        {
                            "type": "STARTED",
                            "title": "STARTED",
                            "achievements": [
                                {"groupId": "FG000", "numSubjects": "397"},
                                {"groupId": "FG001", "numSubjects": "393"},
                            ],
                        },
                        {
                            "type": "COMPLETED",
                            "title": "COMPLETED",
                            "achievements": [
                                {"groupId": "FG000", "numSubjects": "391"},
                                {"groupId": "FG001", "numSubjects": "393"},
                            ],
                        },
                    ],
                    "dropWithdraws": [
                        {
                            "type": "Withdrawal by Subject",
                            "reasons": [
                                {"groupId": "FG000", "numSubjects": "6"},
                                {"groupId": "FG001", "numSubjects": "0"},
                            ],
                        }
                    ],
                }
            ],
        },
    },
}


def test_extract_design_info_full():
    design = extract_design_info(SAMPLE_DATA)

    assert design["allocation"] == "RANDOMIZED"
    assert design["masking"] == "NONE"
    assert design["has_dmc"] is True
    assert design["sponsor_name"] == "ECOG-ACRIN Cancer Research Group"
    assert design["sponsor_class"] == "NETWORK"
    assert "PHASE3" in design["phases"]
    assert design["enrollment"] == 790


def test_extract_design_info_empty():
    assert extract_design_info({}) == {}


def test_extract_design_info_accepts_v2_allocation_key():
    data = {
        "protocolSection": {
            "designModule": {
                "designInfo": {
                    "allocation": "RANDOMIZED",
                    "maskingInfo": {"masking": "NONE"},
                }
            }
        }
    }

    assert extract_design_info(data)["allocation"] == "RANDOMIZED"


def test_extract_description_full():
    desc = extract_description(SAMPLE_DATA)

    assert "PRIMARY OBJECTIVE" in desc
    assert "Overall survival" in desc
    assert "Phase III trial" in desc


def test_extract_description_empty():
    assert extract_description({}) == ""


def test_extract_participant_flow_full():
    flow = extract_participant_flow(SAMPLE_DATA)

    assert "ADT + Docetaxel" in flow
    assert "ADT Alone" in flow
    assert "397" in flow
    assert "Withdrawal by Subject" in flow


def test_extract_participant_flow_no_results():
    data = {"protocolSection": SAMPLE_DATA["protocolSection"]}

    assert extract_participant_flow(data) == ""


def test_format_design_for_prompt_includes_key_fields():
    text = format_design_for_prompt(extract_design_info(SAMPLE_DATA))

    assert "RANDOMIZED" in text
    assert "NONE" in text
    assert "ECOG-ACRIN" in text
    assert "ClinicalTrials.gov" in text


def test_format_design_for_prompt_empty():
    assert "No design metadata" in format_design_for_prompt({})


def test_format_description_for_prompt():
    text = format_description_for_prompt(extract_description(SAMPLE_DATA))

    assert "PRIMARY OBJECTIVE" in text
    assert "pre-specified objectives and analysis" not in text


def test_format_description_for_prompt_empty():
    assert "No description" in format_description_for_prompt("")


def test_format_flow_for_prompt():
    text = format_flow_for_prompt(extract_participant_flow(SAMPLE_DATA))

    assert "ADT" in text


def test_format_flow_for_prompt_empty():
    assert "No participant flow" in format_flow_for_prompt("")
