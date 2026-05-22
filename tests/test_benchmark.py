from io import StringIO
from pathlib import Path
from unittest.mock import patch

from rob2_pipeline.benchmark import (
    _required_supplement_failures,
    compare_judgments,
    find_supplements_for_trial,
    load_reference,
    run_benchmark,
    summarize_benchmark,
    write_benchmark_report,
)


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
            "comparison": {
                "D1": True,
                "D2": False,
                "D3": True,
                "D4": True,
                "D5": True,
                "Overall": True,
            },
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
            "comparison": {
                "D1": False,
                "D2": True,
                "D3": True,
                "D4": True,
                "D5": True,
                "Overall": False,
            },
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


def test_summarize_benchmark_groups_metrics_by_cohort():
    results = [
        {
            "trial": "A",
            "cohort": "calibration",
            "skipped": False,
            "error": None,
            "comparison": {
                "D1": True,
                "D2": True,
                "D3": True,
                "D4": True,
                "D5": True,
                "Overall": True,
            },
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
                    "D1": "Low",
                    "D2": "Low",
                    "D3": "Low",
                    "D4": "Low",
                    "D5": "Low",
                },
                "overall_judgment": "Low",
            },
        },
        {
            "trial": "B",
            "cohort": "validation",
            "skipped": False,
            "error": None,
            "comparison": {
                "D1": False,
                "D2": True,
                "D3": True,
                "D4": True,
                "D5": True,
                "Overall": False,
            },
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
    ]

    summary = summarize_benchmark(results)

    assert summary["cohorts"]["calibration"]["evaluated_trials"] == 1
    assert summary["cohorts"]["calibration"]["agreement_counts"]["Overall"] == {
        "matches": 1,
        "total": 1,
    }
    assert summary["cohorts"]["validation"]["evaluated_trials"] == 1
    assert summary["cohorts"]["validation"]["agreement_counts"]["Overall"] == {
        "matches": 0,
        "total": 1,
    }


def test_write_benchmark_report_hides_unspecified_cohort_when_no_labels(tmp_path):
    results = [
        {
            "id": "TRIAL1:OS",
            "trial": "TRIAL1",
            "outcome": "Outcome A",
            "cohort": "unspecified",
            "skipped": False,
            "error": None,
            "notes": "",
            "comparison": {
                "D1": True,
                "D2": True,
                "D3": True,
                "D4": True,
                "D5": True,
                "Overall": True,
            },
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
                    "D1": "Low",
                    "D2": "Low",
                    "D3": "Low",
                    "D4": "Low",
                    "D5": "Low",
                },
                "overall_judgment": "Low",
            },
        }
    ]
    summary = summarize_benchmark(results)

    write_benchmark_report(results, summary, tmp_path / "benchmark_report.md")

    report = (tmp_path / "benchmark_report.md").read_text(encoding="utf-8")
    assert "## Cohort Agreement" not in report
    assert "| Trial | Outcome | D1 | D2 | D3 | D4 | D5 | Overall | Notes |" in report
    assert "unspecified" not in report


def test_find_supplements_for_trial_handles_spaces_and_case(tmp_path):
    supplement_root = tmp_path / "supplement"
    trial_dir = supplement_root / "SWOG 1216"
    trial_dir.mkdir(parents=True)
    protocol = trial_dir / "protocol_jco.21.02517.pdf"
    dss = trial_dir / "dss_jco.21.02517.pdf"
    protocol.write_bytes(b"pdf")
    dss.write_bytes(b"pdf")

    result = find_supplements_for_trial(supplement_root, "swog 1216")

    assert result == [dss, protocol]


def test_run_benchmark_passes_discovered_supplements(tmp_path, monkeypatch):
    pdf_dir = tmp_path / "benchmark"
    pdf_dir.mkdir()
    (pdf_dir / "TITAN.pdf").write_bytes(b"pdf")
    supplement_root = pdf_dir / "supplement"
    trial_dir = supplement_root / "TITAN"
    trial_dir.mkdir(parents=True)
    protocol = trial_dir / "protocol.pdf"
    protocol.write_bytes(b"pdf")

    reference_csv = tmp_path / "ref.csv"
    reference_csv.write_text(
        "Trial,D1,D2,D3,D4,D5,Overall Risk\nTITAN,Low,Low,Low,Low,Low,Low\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "out"

    calls = []

    def fake_run_assessment(**kwargs):
        calls.append(kwargs)
        assessment_dir = Path(kwargs["output_dir"])
        assessment_dir.mkdir(parents=True)
        (assessment_dir / "TITAN_rob2_data.json").write_text(
            '{"domain_judgments": {}, "overall_judgment": ""}',
            encoding="utf-8",
        )

    monkeypatch.setattr("rob2_pipeline.benchmark.run_assessment", fake_run_assessment)

    results = run_benchmark(
        pdf_dir=pdf_dir,
        reference_csvs={"OS": reference_csv},
        outcome_map=[
            {"trial": "TITAN", "outcome_code": "OS", "cohort": "unspecified"}
        ],
        output_dir=output_dir,
        supplement_dir=supplement_root,
        use_supplements=True,
    )

    assert calls[0]["supplementary_paths"] == [str(protocol)]
    assert results[0]["supplements_found"] == 1


def test_run_benchmark_required_supplements_errors_when_missing(tmp_path):
    pdf_dir = tmp_path / "benchmark"
    pdf_dir.mkdir()
    (pdf_dir / "TITAN.pdf").write_bytes(b"pdf")
    reference_csv = tmp_path / "ref.csv"
    reference_csv.write_text(
        "Trial,D1,D2,D3,D4,D5,Overall Risk\nTITAN,Low,Low,Low,Low,Low,Low\n",
        encoding="utf-8",
    )

    results = run_benchmark(
        pdf_dir=pdf_dir,
        reference_csvs={"OS": reference_csv},
        outcome_map=[{"trial": "TITAN", "outcome_code": "OS"}],
        output_dir=tmp_path / "out",
        supplement_dir=tmp_path / "missing",
        use_supplements=True,
        supplement_policy="required",
    )

    assert results[0]["skipped"] is False
    assert "Required supplements" in results[0]["error"]
    assert "Required supplements" in results[0]["notes"]


def test_run_benchmark_required_supplements_errors_on_parse_failure(
    tmp_path, monkeypatch
):
    pdf_dir = tmp_path / "benchmark"
    pdf_dir.mkdir()
    (pdf_dir / "TITAN.pdf").write_bytes(b"pdf")
    supplement_root = pdf_dir / "supplement"
    trial_dir = supplement_root / "TITAN"
    trial_dir.mkdir(parents=True)
    protocol = trial_dir / "protocol.pdf"
    protocol.write_bytes(b"pdf")

    reference_csv = tmp_path / "ref.csv"
    reference_csv.write_text(
        "Trial,D1,D2,D3,D4,D5,Overall Risk\nTITAN,Low,Low,Low,Low,Low,Low\n",
        encoding="utf-8",
    )

    def fake_run_assessment(**kwargs):
        assessment_dir = Path(kwargs["output_dir"])
        assessment_dir.mkdir(parents=True)
        (assessment_dir / "TITAN_rob2_data.json").write_text(
            """
            {
              "domain_judgments": {},
              "overall_judgment": "",
              "source_documents": [
                {"document_id": "primary", "document_name": "TITAN.pdf", "is_primary": true, "status": "parsed"},
                {"document_id": "supplement:001", "document_name": "protocol.pdf", "is_primary": false, "status": "failed"}
              ]
            }
            """,
            encoding="utf-8",
        )

    monkeypatch.setattr("rob2_pipeline.benchmark.run_assessment", fake_run_assessment)

    results = run_benchmark(
        pdf_dir=pdf_dir,
        reference_csvs={"OS": reference_csv},
        outcome_map=[{"trial": "TITAN", "outcome_code": "OS"}],
        output_dir=tmp_path / "out",
        supplement_dir=supplement_root,
        use_supplements=True,
        supplement_policy="required",
    )

    assert "Required supplement ingestion failed" in results[0]["error"]
    assert results[0]["comparison"] == {}


def test_required_supplement_failures_detects_requested_but_not_ingested():
    failures = _required_supplement_failures(
        [Path("inputs/benchmark/supplement/TITAN/protocol.pdf")],
        [
            {
                "document_id": "primary",
                "path": "inputs/benchmark/TITAN.pdf",
                "is_primary": True,
                "status": "parsed",
            }
        ],
    )

    assert failures == ["protocol.pdf (not ingested)"]


def test_required_supplement_failures_accepts_all_requested_parsed():
    failures = _required_supplement_failures(
        [Path("inputs/benchmark/supplement/TITAN/protocol.pdf")],
        [
            {
                "document_id": "supplement:001",
                "path": "inputs/benchmark/supplement/TITAN/protocol.pdf",
                "is_primary": False,
                "status": "parsed",
            }
        ],
    )

    assert failures == []


def test_required_supplement_failures_accepts_partial_with_window_warnings():
    failures = _required_supplement_failures(
        [Path("inputs/benchmark/supplement/TITAN/protocol.pdf")],
        [
            {
                "document_id": "supplement:001",
                "path": "inputs/benchmark/supplement/TITAN/protocol.pdf",
                "is_primary": False,
                "status": "partial",
                "error": "Supplement page window skipped: std::bad_alloc",
            }
        ],
    )

    assert failures == []
