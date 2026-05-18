"""Diagnostic categorizer for RoB 2 pipeline failures.

Reads per-trial `_trace.json` (LLM I/O from rob2_pipeline.trace) and
`_rob2_data.json` (with rag_sources for retrieved chunks, from Ali's
io.py rename of rag_chunk_metadata) from a benchmark output dir, plus
reference CSVs from data/references/. For each per-domain mismatch,
classifies the failure as RAG-miss vs LLM-miss vs ambiguous and dumps
the supporting context (retrieved chunks, LLM prompts/responses).

Outputs:
- diagnostic_summary.csv: one row per (trial, outcome, domain)
- diagnostic_report.md: per-failure detail with classification reasoning

Heuristic:
- rag_likely_miss: max chunk similarity < 0.3 OR LLM signaled "no
  evidence / not reported / cannot determine" pattern
- llm_likely_miss: top-3 average similarity >= 0.5 AND LLM did not
  signal no-evidence (chunks were available, model misjudged)
- ambiguous: everything in between
- match: pipeline matched reference (no failure to classify)
- no_data: empty trace + empty chunks

Additional flag (LLM-miss only): `looks_ungrounded` is True when the
LLM response has no >=20-char verbatim substring overlap with any
retrieved chunk. Catches the "LLM produced a generic training-data
answer instead of citing retrieved evidence" failure mode.
"""

import argparse
import csv
import difflib
import json
import re
from pathlib import Path
from typing import Any

DOMAINS = ("D1", "D2", "D3", "D4", "D5")

DOMAIN_RAG_KEYS = {
    "D1": ["d1"],
    "D2": ["d2"],
    "D3": ["d3"],
    "D4": ["d4"],
    "D5": ["d5"],
}

DOMAIN_NODE_PREFIXES = {
    "D1": "domain1",
    "D2": "domain2",
    "D3": "domain3",
    "D4": "domain4",
    "D5": "domain5",
}

NO_EVIDENCE_PATTERNS = [
    r"\bno evidence\b",
    r"\bnot reported\b",
    r"\bcannot determine\b",
    r"\binsufficient information\b",
    r"\bno information\b",
    r"\bunable to assess\b",
]

UNGROUNDED_MIN_OVERLAP_CHARS = 20


def _normalize_judgment(value: Any) -> str:
    if not value:
        return ""
    raw = str(value).strip()
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


def load_reference_csv(csv_path: Path) -> dict[str, dict[str, str]]:
    refs: dict[str, dict[str, str]] = {}
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            trial = (row.get("Trial") or "").strip()
            if not trial:
                continue
            refs[trial.casefold()] = {
                "trial": trial,
                "D1": _normalize_judgment(row.get("D1")),
                "D2": _normalize_judgment(row.get("D2")),
                "D3": _normalize_judgment(row.get("D3")),
                "D4": _normalize_judgment(row.get("D4")),
                "D5": _normalize_judgment(row.get("D5")),
                "Overall": _normalize_judgment(row.get("Overall Risk")),
            }
    return refs


def find_run_outputs(benchmark_dir: Path) -> list[Path]:
    """Return directories that look like per-run output dirs.

    A per-run dir has both a `_trace.json` (from rob2_pipeline.trace) and
    a `_rob2_data.json` (from rob2_pipeline.pipeline) with the same stem.
    """
    return [p for p in benchmark_dir.iterdir() if p.is_dir() and any(p.glob("*_trace.json"))]


def load_run(run_dir: Path) -> dict[str, Any] | None:
    trace_files = list(run_dir.glob("*_trace.json"))
    data_files = list(run_dir.glob("*_rob2_data.json"))
    if not trace_files or not data_files:
        return None
    trace = json.loads(trace_files[0].read_text())
    data = json.loads(data_files[0].read_text())
    return {"trace": trace, "data": data, "dir_name": run_dir.name}


def chunks_for_domain(data: dict, domain: str) -> list[dict]:
    """Read chunks for a domain from Ali's rag_sources (LangChain Document shape).

    Returns chunks with keys: text, section, page_numbers, score.
    """
    rag_sources = data.get("rag_sources") or {}
    keys = set(DOMAIN_RAG_KEYS[domain])
    out: list[dict] = []
    for key in keys:
        chunks = rag_sources.get(key) or []
        out.extend(chunks)
    return out


def llm_calls_for_domain(trace: dict, domain: str) -> list[dict]:
    prefix = DOMAIN_NODE_PREFIXES[domain]
    return [c for c in trace.get("llm_calls", []) if (c.get("node") or "").startswith(prefix)]


def looks_ungrounded(response: str, chunks: list[dict], min_overlap_chars: int = UNGROUNDED_MIN_OVERLAP_CHARS) -> bool:
    """True if `response` has no >=min_overlap_chars verbatim substring in any chunk.

    Catches the failure mode where the LLM produced a generic-sounding
    answer with no overlap to the retrieved chunks — suggests the answer
    came from training data, not the evidence in front of it.
    """
    if not response or not chunks:
        return False
    for chunk in chunks:
        chunk_text = chunk.get("text") or ""
        if not chunk_text:
            continue
        matcher = difflib.SequenceMatcher(None, response, chunk_text, autojunk=False)
        match = matcher.find_longest_match(0, len(response), 0, len(chunk_text))
        if match.size >= min_overlap_chars:
            return False
    return True


def heuristic_classify(chunks: list[dict], llm_calls: list[dict]) -> tuple[str, dict]:
    """Return (classification, evidence dict).

    Classifications: rag_likely_miss, llm_likely_miss, ambiguous, no_data.
    """
    if not chunks and not llm_calls:
        return "no_data", {"reason": "no RAG retrieval and no LLM calls for this domain"}

    scores = [c.get("score", 0.0) for c in chunks]
    max_score = max(scores) if scores else 0.0
    avg_top3 = sum(sorted(scores, reverse=True)[:3]) / max(1, min(3, len(scores)))

    responses_text = " ".join((c.get("response") or "") for c in llm_calls).casefold()
    has_no_evidence_signal = any(re.search(p, responses_text) for p in NO_EVIDENCE_PATTERNS)

    evidence: dict[str, Any] = {
        "max_similarity_score": round(max_score, 3),
        "avg_top3_similarity": round(avg_top3, 3),
        "n_chunks_retrieved": len(chunks),
        "n_llm_calls": len(llm_calls),
        "llm_signaled_no_evidence": has_no_evidence_signal,
        "looks_ungrounded": False,
    }

    if max_score < 0.3 or has_no_evidence_signal:
        return "rag_likely_miss", evidence
    if avg_top3 >= 0.5 and not has_no_evidence_signal:
        joined_response = "\n\n".join((c.get("response") or "") for c in llm_calls)
        evidence["looks_ungrounded"] = looks_ungrounded(joined_response, chunks)
        return "llm_likely_miss", evidence
    return "ambiguous", evidence


def _outcome_code_from_label(outcome: str | None) -> str | None:
    outcome_lc = (outcome or "").casefold()
    if "overall survival" in outcome_lc:
        return "OS"
    if "progression" in outcome_lc:
        return "PFS"
    if "adverse" in outcome_lc:
        return "AE"
    return None


def categorize_run(run: dict, reference_csvs: dict[str, Path]) -> list[dict]:
    trace = run["trace"]
    data = run["data"]
    trial = trace.get("trial", "")
    outcome = trace.get("outcome", "")
    outcome_code = _outcome_code_from_label(outcome)

    ref_csv = reference_csvs.get(outcome_code) if outcome_code else None
    if ref_csv is None:
        return []
    refs = load_reference_csv(ref_csv)
    ref_row = refs.get(trial.casefold())
    if ref_row is None:
        return []

    pipeline_judgments = data.get("domain_judgments") or {}
    rows: list[dict] = []
    for domain in DOMAINS:
        pipeline_value = _normalize_judgment(pipeline_judgments.get(domain, ""))
        reference_value = ref_row.get(domain, "")
        matched = pipeline_value.casefold() == reference_value.casefold() and pipeline_value != ""

        chunks = chunks_for_domain(data, domain)
        llm_calls = llm_calls_for_domain(trace, domain)
        classification, evidence = (
            ("match", {}) if matched else heuristic_classify(chunks, llm_calls)
        )

        rows.append({
            "trial": trial,
            "outcome_code": outcome_code,
            "domain": domain,
            "pipeline_judgment": pipeline_value,
            "reference_judgment": reference_value,
            "matched": matched,
            "classification": classification,
            **evidence,
            "_chunks": chunks,
            "_llm_calls": llm_calls,
        })
    return rows


def write_summary_csv(rows: list[dict], path: Path) -> None:
    fields = [
        "trial", "outcome_code", "domain",
        "pipeline_judgment", "reference_judgment", "matched", "classification",
        "max_similarity_score", "avg_top3_similarity",
        "n_chunks_retrieved", "n_llm_calls", "llm_signaled_no_evidence",
        "looks_ungrounded",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_detail_report(rows: list[dict], path: Path) -> None:
    failures = [r for r in rows if not r["matched"] and r["classification"] != "match"]
    lines: list[str] = []
    lines.append("# Diagnostic Report: Per-Failure Detail")
    lines.append("")
    lines.append(f"Total runs analyzed: {len({(r['trial'], r['outcome_code']) for r in rows})}")
    lines.append(f"Total domain assessments: {len(rows)}")
    lines.append(f"Total mismatches: {len(failures)}")
    lines.append("")

    by_class: dict[str, int] = {}
    for r in failures:
        by_class[r["classification"]] = by_class.get(r["classification"], 0) + 1
    lines.append("## Failures by Heuristic Classification")
    lines.append("")
    for cls, count in sorted(by_class.items(), key=lambda x: -x[1]):
        lines.append(f"- {cls}: {count}")
    ungrounded_count = sum(1 for r in failures if r.get("looks_ungrounded"))
    if ungrounded_count:
        lines.append(f"- (of which) llm_likely_miss + looks_ungrounded: {ungrounded_count}")
    lines.append("")

    by_domain: dict[str, dict[str, int]] = {}
    for r in rows:
        d = r["domain"]
        by_domain.setdefault(d, {"total": 0, "match": 0})
        by_domain[d]["total"] += 1
        if r["matched"]:
            by_domain[d]["match"] += 1
    lines.append("## Per-Domain Accuracy")
    lines.append("")
    lines.append("| Domain | Accuracy | Matches/Total |")
    lines.append("| --- | ---: | --- |")
    for d in DOMAINS:
        stats = by_domain.get(d, {"total": 0, "match": 0})
        rate = (stats["match"] / stats["total"] * 100) if stats["total"] else 0.0
        lines.append(f"| {d} | {rate:.1f}% | {stats['match']}/{stats['total']} |")
    lines.append("")

    lines.append("## Per-Failure Detail")
    lines.append("")
    for r in failures:
        lines.append(f"### {r['trial']} ({r['outcome_code']}) {r['domain']}")
        lines.append("")
        lines.append(f"- Pipeline: **{r['pipeline_judgment']}**  |  Reference: **{r['reference_judgment']}**")
        lines.append(f"- Classification: **{r['classification']}**")
        if r["classification"] == "llm_likely_miss":
            lines.append(f"- Looks ungrounded (no >={UNGROUNDED_MIN_OVERLAP_CHARS}-char overlap with any chunk): **{r.get('looks_ungrounded', False)}**")
        lines.append(f"- Max similarity: {r.get('max_similarity_score', 'n/a')} | Top-3 avg: {r.get('avg_top3_similarity', 'n/a')}")
        lines.append(f"- Chunks retrieved: {r.get('n_chunks_retrieved', 0)} | LLM calls: {r.get('n_llm_calls', 0)}")
        lines.append(f"- LLM signaled 'no evidence': {r.get('llm_signaled_no_evidence', False)}")
        lines.append("")

        chunks = r["_chunks"][:5]
        if chunks:
            lines.append("**Top RAG chunks (truncated to 5):**")
            lines.append("")
            for i, c in enumerate(chunks):
                section = c.get("section", "")
                score = c.get("score", 0.0)
                text = (c.get("text") or "").replace("\n", " ")[:300]
                lines.append(f"{i+1}. `[{section} | sim={score:.3f}]` {text}...")
            lines.append("")

        for c in r["_llm_calls"]:
            node = c.get("node", "")
            response = (c.get("response") or "").strip()
            response_excerpt = response[:800] + ("..." if len(response) > 800 else "")
            lines.append(f"**LLM call: {node}**")
            lines.append("")
            lines.append("```")
            lines.append(response_excerpt)
            lines.append("```")
            lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Categorize RoB 2 pipeline failures from trace + rob2_data JSONs.")
    parser.add_argument("--benchmark-dir", default="outputs/benchmark", help="Directory containing per-run subdirs.")
    parser.add_argument("--reference-dir", default="data/references", help="Directory with reference CSVs.")
    parser.add_argument("--output-dir", default="outputs/diagnostic", help="Where to write summary CSV + report.")
    args = parser.parse_args()

    benchmark_dir = Path(args.benchmark_dir)
    ref_dir = Path(args.reference_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    reference_csvs = {
        "OS": ref_dir / "overall_survival.csv",
        "PFS": ref_dir / "progression_free_survival.csv",
        "AE": ref_dir / "adverse_events.csv",
    }

    run_dirs = find_run_outputs(benchmark_dir)
    if not run_dirs:
        print(f"No run directories with trace.json found in {benchmark_dir}")
        return

    all_rows: list[dict] = []
    for run_dir in sorted(run_dirs):
        run = load_run(run_dir)
        if run is None:
            continue
        rows = categorize_run(run, reference_csvs)
        all_rows.extend(rows)
        print(f"  {run_dir.name}: {len(rows)} domain assessments")

    summary_path = out_dir / "diagnostic_summary.csv"
    report_path = out_dir / "diagnostic_report.md"
    write_summary_csv(all_rows, summary_path)
    write_detail_report(all_rows, report_path)
    print(f"\nWrote {summary_path}")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
