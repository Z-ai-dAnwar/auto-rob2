import csv
import json
import logging
from pathlib import Path
from typing import Any

from rob2_pipeline.pipeline import run_assessment


LOGGER = logging.getLogger(__name__)
DOMAINS = ("D1", "D2", "D3", "D4", "D5")
OUTCOME_LABELS = {
    "OS": "Overall Survival",
    "PFS": "Progression-Free Survival",
    "AE": "Adverse Events",
}
JUDGMENT_ORDER = ("Low", "Some concerns", "High")


def _strip(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_trial(value: str) -> str:
    return _strip(value).casefold()


def _normalize_judgment(value: Any) -> str:
    raw = _strip(value)
    compact = " ".join(raw.split()).casefold()
    mapping = {
        "l": "Low",
        "low": "Low",
        "s": "Some concerns",
        "some concerns": "Some concerns",
        "h": "High",
        "high": "High",
    }
    return mapping.get(compact, raw)


def _find_pdf_for_trial(pdf_dir: Path, trial_name: str) -> Path | None:
    direct = pdf_dir / f"{trial_name}.pdf"
    if direct.exists() and direct.is_file():
        return direct
    target = f"{trial_name}.pdf".casefold()
    for candidate in pdf_dir.glob("*.pdf"):
        if candidate.is_file() and candidate.name.casefold() == target:
            return candidate
    return None


def find_supplements_for_trial(supplement_dir: Path, trial_name: str) -> list[Path]:
    if not supplement_dir.exists() or not supplement_dir.is_dir():
        return []
    target = trial_name.strip().casefold()
    for candidate in supplement_dir.iterdir():
        if candidate.is_dir() and candidate.name.strip().casefold() == target:
            return sorted(path for path in candidate.glob("*.pdf") if path.is_file())
    return []


def _required_supplement_failures(
    requested_paths: list[Path], source_documents: list[dict]
) -> list[str]:
    def key(value: object) -> str:
        text = _strip(value)
        if not text:
            return ""
        try:
            text = str(Path(text).resolve())
        except OSError:
            pass
        return text.replace("\\", "/").casefold()

    non_primary_documents = [
        document for document in source_documents if not document.get("is_primary")
    ]
    documents_by_path = {
        key(document.get("path")): document
        for document in non_primary_documents
        if _strip(document.get("path"))
    }
    failures: list[str] = []
    for requested in requested_paths:
        requested_key = key(requested)
        document = documents_by_path.get(requested_key)
        if document is None:
            failures.append(f"{requested.name} (not ingested)")
        elif document.get("status") not in {"parsed", "partial"}:
            failures.append(f"{requested.name} ({document.get('status', 'unknown')})")
    return failures


def _iter_outcome_map(outcome_map) -> list[tuple[str, str, str]]:
    if isinstance(outcome_map, dict):
        return [(trial, code, "unspecified") for trial, code in outcome_map.items()]
    pairs = []
    for item in outcome_map:
        if isinstance(item, dict):
            pairs.append(
                (item["trial"], item["outcome_code"], item.get("cohort", "unspecified"))
            )
        else:
            if len(item) == 2:
                trial, outcome_code = item
                cohort = "unspecified"
            else:
                trial, outcome_code, cohort = item
            pairs.append((trial, outcome_code, cohort))
    return pairs


def load_reference(csv_path: Path) -> dict[str, dict]:
    references: dict[str, dict] = {}
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            trial = _strip(row.get("Trial"))
            if not trial:
                continue
            references[trial] = {
                "D1": _strip(row.get("D1")),
                "D2": _strip(row.get("D2")),
                "D3": _strip(row.get("D3")),
                "D4": _strip(row.get("D4")),
                "D5": _strip(row.get("D5")),
                "Overall Risk": _strip(row.get("Overall Risk")),
            }
    return references


def compare_judgments(pipeline: dict, reference: dict) -> dict[str, bool]:
    domain_judgments = pipeline.get("domain_judgments") or {}
    result: dict[str, bool] = {}
    for domain in DOMAINS:
        left = _normalize_judgment(domain_judgments.get(domain, ""))
        right = _normalize_judgment(reference.get(domain, ""))
        result[domain] = left.casefold() == right.casefold()

    overall_pipeline = _normalize_judgment(pipeline.get("overall_judgment", ""))
    overall_ref = _normalize_judgment(reference.get("Overall Risk", ""))
    result["Overall"] = overall_pipeline.casefold() == overall_ref.casefold()
    return result


def run_benchmark(
    pdf_dir,
    reference_csvs,
    outcome_map,
    output_dir,
    supplement_dir=None,
    use_supplements: bool = False,
    supplement_policy: str = "auto",
    **run_kwargs,
) -> list[dict]:
    pdf_dir_path = Path(pdf_dir)
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    normalized_refs: dict[str, dict[str, dict]] = {}
    for outcome_code, csv_path in reference_csvs.items():
        loaded = load_reference(Path(csv_path))
        normalized_refs[outcome_code.upper()] = {
            _normalize_trial(trial): {"trial": trial, "row": row}
            for trial, row in loaded.items()
        }

    results: list[dict] = []
    for trial_name, outcome_code, cohort in _iter_outcome_map(outcome_map):
        code = _strip(outcome_code).upper()
        outcome_label = OUTCOME_LABELS.get(code, "")
        trial_result: dict[str, Any] = {
            "id": f"{trial_name}:{code}",
            "trial": trial_name,
            "outcome_code": code,
            "outcome": outcome_label,
            "cohort": _strip(cohort) or "unspecified",
            "supplementary_paths": [],
            "supplements_found": 0,
            "supplement_policy": supplement_policy,
            "skipped": False,
            "error": None,
            "notes": "",
        }

        references_for_outcome = normalized_refs.get(code)
        if references_for_outcome is None:
            trial_result["skipped"] = True
            trial_result["notes"] = f"Unknown outcome code: {code}"
            LOGGER.warning(
                "Skipping trial %s: unknown outcome code '%s'", trial_name, code
            )
            results.append(trial_result)
            continue

        reference_row_entry = references_for_outcome.get(_normalize_trial(trial_name))
        if reference_row_entry is None:
            trial_result["skipped"] = True
            trial_result["notes"] = "Trial not in reference"
            LOGGER.warning(
                "Skipping trial %s: not present in %s reference", trial_name, code
            )
            results.append(trial_result)
            continue

        pdf_path = _find_pdf_for_trial(pdf_dir_path, trial_name)
        if pdf_path is None:
            trial_result["skipped"] = True
            trial_result["notes"] = f"PDF not found in {pdf_dir_path}"
            LOGGER.warning(
                "Skipping trial %s: PDF not found in %s", trial_name, pdf_dir_path
            )
            results.append(trial_result)
            continue

        trial_result["pdf_path"] = str(pdf_path)
        trial_result["reference"] = reference_row_entry["row"]
        assessment_output_dir = output_dir_path / f"{pdf_path.stem}_{code.lower()}"
        supplement_paths: list[Path] = []
        if (
            use_supplements
            and supplement_policy != "none"
            and supplement_dir is not None
        ):
            supplement_paths = find_supplements_for_trial(
                Path(supplement_dir), trial_name
            )
        trial_result["supplementary_paths"] = [str(path) for path in supplement_paths]
        trial_result["supplements_found"] = len(supplement_paths)
        if use_supplements and supplement_policy == "required" and not supplement_paths:
            trial_result["error"] = (
                f"Required supplements not found in {supplement_dir}"
            )
            trial_result["notes"] = trial_result["error"]
            trial_result["comparison"] = {}
            results.append(trial_result)
            continue

        try:
            run_assessment(
                pdf_path=str(pdf_path),
                outcome=outcome_label,
                output_dir=str(assessment_output_dir),
                supplementary_paths=[str(path) for path in supplement_paths],
                **run_kwargs,
            )
            output_json = assessment_output_dir / f"{pdf_path.stem}_rob2_data.json"
            pipeline_output = json.loads(output_json.read_text(encoding="utf-8"))
            if supplement_policy == "required":
                failures = _required_supplement_failures(
                    supplement_paths,
                    list(pipeline_output.get("source_documents") or []),
                )
                if failures:
                    raise RuntimeError(
                        "Required supplement ingestion failed: " + ", ".join(failures)
                    )
            trial_result["pipeline"] = {
                "domain_judgments": pipeline_output.get("domain_judgments") or {},
                "overall_judgment": pipeline_output.get("overall_judgment"),
            }
            trial_result["comparison"] = compare_judgments(
                trial_result["pipeline"], reference_row_entry["row"]
            )
        except Exception as exc:  # noqa: BLE001
            trial_result["error"] = str(exc)
            trial_result["notes"] = str(exc)
            trial_result["comparison"] = {}
            LOGGER.exception("run_assessment failed for trial %s", trial_name)

        results.append(trial_result)

    return results


def _empty_confusion() -> dict[str, dict[str, int]]:
    return {row: {col: 0 for col in JUDGMENT_ORDER} for row in JUDGMENT_ORDER}


def _summarize_results_subset(results) -> dict:
    fields = [*DOMAINS, "Overall"]
    counts = {field: {"matches": 0, "total": 0} for field in fields}
    confusion = {field: _empty_confusion() for field in fields}

    evaluated_trials = 0
    for result in results:
        if result.get("error") or result.get("skipped"):
            continue
        comparison = result.get("comparison") or {}
        reference = result.get("reference") or {}
        pipeline = result.get("pipeline") or {}
        domain_judgments = pipeline.get("domain_judgments") or {}
        evaluated_trials += 1

        for domain in DOMAINS:
            if domain in comparison:
                counts[domain]["total"] += 1
                counts[domain]["matches"] += 1 if comparison[domain] else 0
            ref_value = _normalize_judgment(reference.get(domain, ""))
            pred_value = _normalize_judgment(domain_judgments.get(domain, ""))
            if ref_value in JUDGMENT_ORDER and pred_value in JUDGMENT_ORDER:
                confusion[domain][ref_value][pred_value] += 1

        if "Overall" in comparison:
            counts["Overall"]["total"] += 1
            counts["Overall"]["matches"] += 1 if comparison["Overall"] else 0
        overall_ref = _normalize_judgment(reference.get("Overall Risk", ""))
        overall_pred = _normalize_judgment(pipeline.get("overall_judgment", ""))
        if overall_ref in JUDGMENT_ORDER and overall_pred in JUDGMENT_ORDER:
            confusion["Overall"][overall_ref][overall_pred] += 1

    rates = {}
    for field, field_counts in counts.items():
        total = field_counts["total"]
        rates[field] = (field_counts["matches"] / total) if total else 0.0

    return {
        "evaluated_trials": evaluated_trials,
        "agreement_counts": counts,
        "agreement_rates": rates,
        "confusion_matrices": confusion,
        "judgment_order": list(JUDGMENT_ORDER),
    }


def summarize_benchmark(results) -> dict:
    summary = _summarize_results_subset(results)
    cohorts: dict[str, list[dict]] = {}
    for result in results:
        cohort = _strip(result.get("cohort")) or "unspecified"
        cohorts.setdefault(cohort, []).append(result)
    summary["cohorts"] = {
        cohort: _summarize_results_subset(items)
        for cohort, items in sorted(cohorts.items())
    }
    return summary


def write_benchmark_report(results, summary, output_path):
    output_path = Path(output_path)
    report_path = output_path.parent / "benchmark_report.md"
    json_path = output_path.parent / "benchmark_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(
        json.dumps(
            {"results": results, "summary": summary}, indent=2, ensure_ascii=False
        ),
        encoding="utf-8",
    )

    fields = [*DOMAINS, "Overall"]
    has_meaningful_cohort = any(
        (_strip(result.get("cohort")) or "unspecified") != "unspecified"
        for result in results
    )
    lines = [
        "# Benchmark Report",
        "",
        f"- Trials evaluated: {summary.get('evaluated_trials', 0)}",
        "",
        "## Summary Agreement",
        "",
        "| Field | Agreement |",
        "| --- | ---: |",
    ]
    for field in fields:
        counts = summary.get("agreement_counts", {}).get(
            field, {"matches": 0, "total": 0}
        )
        rate = summary.get("agreement_rates", {}).get(field, 0.0) * 100
        lines.append(
            f"| {field} | {rate:.1f}% ({counts['matches']}/{counts['total']}) |"
        )

    if has_meaningful_cohort and summary.get("cohorts"):
        lines.extend(
            [
                "",
                "## Cohort Agreement",
                "",
                "| Cohort | Field | Agreement |",
                "| --- | --- | ---: |",
            ]
        )
        for cohort, cohort_summary in summary["cohorts"].items():
            for field in fields:
                counts = cohort_summary.get("agreement_counts", {}).get(
                    field, {"matches": 0, "total": 0}
                )
                rate = cohort_summary.get("agreement_rates", {}).get(field, 0.0) * 100
                lines.append(
                    f"| {cohort} | {field} | {rate:.1f}% ({counts['matches']}/{counts['total']}) |"
                )

    lines.extend(["", "## Per-Trial Details", ""])
    if has_meaningful_cohort:
        lines.extend(
            [
                "| Trial | Outcome | Cohort | D1 | D2 | D3 | D4 | D5 | Overall | Notes |",
                "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
    else:
        lines.extend(
            [
                "| Trial | Outcome | D1 | D2 | D3 | D4 | D5 | Overall | Notes |",
                "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ]
        )
    for result in results:
        comparison = result.get("comparison") or {}

        def mark(field: str) -> str:
            value = comparison.get(field)
            if value is True:
                return "Y"
            if value is False:
                return "N"
            return "-"

        notes = _strip(result.get("notes"))
        if not notes and result.get("error"):
            notes = _strip(result.get("error"))
        notes = notes[:80]

        row = [
            _strip(result.get("id")) or _strip(result.get("trial")),
            _strip(result.get("outcome")) or _strip(result.get("outcome_code")),
        ]
        if has_meaningful_cohort:
            row.append(_strip(result.get("cohort")) or "unspecified")
        row.extend(
            [
                mark("D1"),
                mark("D2"),
                mark("D3"),
                mark("D4"),
                mark("D5"),
                mark("Overall"),
                notes or "-",
            ]
        )

        lines.append("| " + " | ".join(row) + " |")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
