from io import StringIO
from pathlib import Path
from unittest.mock import patch

from rob2_pipeline.benchmark import compare_judgments, load_reference, summarize_benchmark


def test_load_reference_strips_whitespace():
    csv_text = (
        "Trial,D1,D2,D3,D4,D5,Overall Risk\n"
        " CHAARTED , L , S , L , L , H , Some Concerns \n"
    )

    with patch("pathlib.Path.open", return_value=StringIO(csv_text)):
        data = load_reference(Path("dummy.csv"))

    assert data == {
        "CHAARTED": {
            "D1": "L",
            "D2": "S",
            "D3": "L",
            "D4": "L",
            "D5": "H",
            "Overall Risk": "Some Concerns",
        }
    }


def test_compare_judgments_case_and_compact_normalization():
    pipeline = {
        "domain_judgments": {
            "D1": " low ",
            "D2": "Some concerns",
            "D3": "HIGH",
            "D4": "Low",
            "D5": "Some Concerns",
        },
        "overall_judgment": " high ",
    }
    reference = {
        "D1": "L",
        "D2": "s",
        "D3": "h",
        "D4": " L ",
        "D5": "S",
        "Overall Risk": "H",
    }

    assert compare_judgments(pipeline, reference) == {
        "D1": True,
        "D2": True,
        "D3": True,
        "D4": True,
        "D5": True,
        "Overall": True,
    }


def test_summarize_benchmark_agreement_and_confusion_dicts():
    results = [
        {
            "trial": "A",
            "skipped": False,
            "error": None,
            "comparison": {"D1": True, "D2": False, "D3": True, "D4": True, "D5": True, "Overall": True},
            "reference": {
                "D1": "Low",
                "D2": "Some concerns",
                "D3": "High",
                "D4": "Low",
                "D5": "Low",
                "Overall Risk": "Some concerns",
            },
            "pipeline": {
                "domain_judgments": {
                    "D1": "Low",
                    "D2": "Low",
                    "D3": "High",
                    "D4": "Low",
                    "D5": "Low",
                },
                "overall_judgment": "Some concerns",
            },
        },
        {
            "trial": "B",
            "skipped": False,
            "error": None,
            "comparison": {"D1": False, "D2": True, "D3": True, "D4": True, "D5": True, "Overall": False},
            "reference": {
                "D1": "Low",
                "D2": "Low",
                "D3": "Low",
                "D4": "Low",
                "D5": "Low",
                "Overall Risk": "Low",
            },
            "pipeline": {
                "domain_judgments": {
                    "D1": "High",
                    "D2": "Low",
                    "D3": "Low",
                    "D4": "Low",
                    "D5": "Low",
                },
                "overall_judgment": "High",
            },
        },
        {"trial": "C", "skipped": True, "error": None, "comparison": {}},
    ]

    summary = summarize_benchmark(results)

    assert summary["evaluated_trials"] == 2
    assert summary["agreement_counts"]["D1"] == {"matches": 1, "total": 2}
    assert summary["agreement_rates"]["Overall"] == 0.5
    assert summary["confusion_matrices"]["D1"]["Low"]["Low"] == 1
    assert summary["confusion_matrices"]["D1"]["Low"]["High"] == 1
    assert summary["confusion_matrices"]["Overall"]["Low"]["High"] == 1
