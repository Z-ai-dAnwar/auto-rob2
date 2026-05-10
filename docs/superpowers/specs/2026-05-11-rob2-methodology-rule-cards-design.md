# Spec: RoB 2 Methodology Rule Cards

**Date:** 2026-05-11
**Status:** Approved design

## Context

Recent benchmark-focused prompt changes improved visible failures but risk overfitting the pipeline to a small set of calibration trials. The pipeline should perform well on arbitrary randomized controlled trial inputs by grounding prompts in canonical RoB 2 methodology rather than benchmark-specific wording.

The attached Sterne et al. 2019 BMJ paper and RoB 2 supplementary material are the canonical sources for this design. The goal is to keep valid prompt fixes, rewrite them as domain-agnostic RoB 2 principles, and add evaluation safeguards that make overfitting visible.

## Goals

- Create a canonical, typed methodology layer for RoB 2 signaling-question guidance.
- Render methodology guidance into prompts from reusable rule cards instead of embedding long prompt-specific prose.
- Preserve the current runtime graph, XML response contracts, parsers, and deterministic judge logic.
- Replace brittle exact prompt wording tests with structure, rendering, integration, and evaluation tests.
- Add benchmark reporting metadata that separates visible calibration trials from held-out validation trials.

## Non-Goals

- Do not implement deterministic extraction heuristics unless a rule is truly mechanical and already represented in existing judges.
- Do not change RoB 2 judge algorithms as part of this design.
- Do not make benchmark cohort labels influence assessment behavior.
- Do not encode visible benchmark verdicts, trial names, or disease-specific shortcuts in methodology guidance.

## Architecture

Add a methodology package under `rob2_pipeline/methodology/` that becomes the canonical source for RoB 2 guidance used by prompts.

Core types:

- `Citation`: source label and location, such as `Sterne 2019 supplement p.7` or `BMJ 2019 p.3`.
- `ResponseRule`: guidance for one response option, such as `Y`, `PY`, `PN`, `N`, `NI`, or `NA`.
- `RuleCard`: one signaling question, including SQ ID, question text, response rules, applicability or skip notes, algorithm implications, and citations.
- `DomainMethodology`: groups rule cards, domain-level principles, and judge-algorithm notes.

The rule cards should be compact and source-backed. They may include generic examples when examples come from Sterne/RoB 2 guidance. Disease-specific examples are allowed only when the source guidance itself uses them, such as second-line chemotherapy in Domain 3 missing-data guidance.

## Components

### Methodology Data

Create `rob2_pipeline/methodology/` with:

- `types.py`: typed dataclasses for citations, response rules, rule cards, and domain methodology.
- `domain1.py` through `domain5.py`: canonical RoB 2 rule cards for each domain.
- `render.py`: helper functions that render selected domain methodology into compact prompt sections.
- `__init__.py`: exports domain methodology objects and lookup helpers.

### Prompt Integration

Update `rob2_pipeline/prompts.py` so domain prompts keep their evidence sections and XML output schemas, but obtain SQ guidance from rendered methodology blocks.

Prompts should remain readable. The objective is not to make prompts minimal at all costs; it is to make the source of methodological guidance canonical, reusable, and auditable.

### Benchmark Metadata

Extend benchmark result handling so trial/outcome runs can carry a cohort label:

- `calibration`: visible trials used while developing prompt/methodology changes.
- `validation`: held-out trials used to evaluate generalization.
- `unspecified`: default when no cohort metadata is provided.

Benchmark summaries and reports should keep current aggregate accuracy and add per-cohort agreement counts/rates.

### Tests

Tests should verify methodology structure and prompt integration without asserting fragile exact prose.

Required test categories:

- Every domain has expected SQ IDs and response options.
- Every rule card has at least one citation.
- Renderer output includes stable SQ IDs, answer options, and citation labels.
- Missing rule IDs raise clear errors.
- Formatted prompts include methodology blocks, outcome/effect context, evidence sections, and XML schemas.
- Methodology/rendered prompt guidance does not contain visible benchmark trial names such as `CHAARTED`, `PEACE-1`, or `STAMPEDE`.
- Benchmark summaries can separate calibration and validation cohorts without changing judgments.

Existing parser and judge tests remain the source of deterministic algorithm correctness.

## Data Flow

Runtime assessment flow remains unchanged:

1. Ingest PDF and extract evidence.
2. Retrieve local RAG context.
3. Domain node formats prompt.
4. LLM returns XML signaling-question answers.
5. XML parser extracts SQ answers.
6. Deterministic judges produce domain and overall judgments.
7. Report formatter writes outputs.

Prompt construction changes at step 3:

1. `prompts.py` imports or receives the relevant `DomainMethodology`.
2. `render_methodology(domain, sq_ids)` creates a compact canonical guidance block.
3. The prompt includes this block after evidence sections and before XML output instructions.
4. The LLM answers the same XML fields as today.

Benchmark flow changes only in reporting:

1. CLI or benchmark input metadata optionally labels each run with a cohort.
2. `run_benchmark` stores `cohort` on each result item.
3. `summarize_benchmark` reports aggregate metrics and per-cohort metrics.
4. `write_benchmark_report` displays overall accuracy first, then cohort-specific accuracy.

## Error Handling And Guardrails

- Missing requested rule cards should raise clear developer errors during rendering or tests.
- Rule cards without citations should fail tests.
- Applicability and skip rules should be explicit metadata, not hidden only in prose.
- Prompt rendering should avoid trial names, benchmark labels, and disease-specific examples unless directly sourced from RoB 2 guidance.
- Benchmark cohort labels must not alter pipeline behavior.
- Existing deterministic judges remain the final arbiters once SQ answers are parsed.
- Exact prompt wording tests should be avoided except for stable identifiers such as SQ IDs, citation labels, and XML tags.
- Prompt changes should be accepted only when justified by canonical methodology and not by a visible benchmark verdict alone.

## Testing And Verification

Unit tests:

- Validate methodology objects for all five domains.
- Validate renderer behavior and errors.
- Validate prompt integration without exact wording coupling.
- Validate no visible benchmark trial names leak into methodology guidance.
- Validate benchmark cohort summary/report logic.

Regression verification:

- Run `uv run python -m pytest tests/`.
- Run benchmark dry-runs to confirm input/reference resolution.
- Treat LLM-backed benchmark runs as evaluation artifacts, not unit tests.

Benchmark evaluation should report whether visible calibration accuracy and held-out validation accuracy move together. A change that improves calibration but worsens validation should be treated as possible overfitting even if aggregate accuracy improves.

## Implementation Notes

- Start with rule-card coverage for the five current domains and all currently prompted SQs.
- Keep the first implementation focused: methodology data, renderer, prompt integration, and cohort reporting.
- Defer deterministic pre-checks or extraction helpers unless a later design identifies a mechanical rule that can be safely implemented.
- Existing uncommitted benchmark-prompt edits should be generalized through the rule-card layer rather than preserved as prompt-local special cases.

## Open Decisions Resolved

- Store canonical guidance in Python modules, not YAML or runtime source-PDF retrieval.
- Use curated summaries with citations, not full copied source text.
- Use rule-card and rendering tests rather than exact prompt wording assertions.
- Include only a narrow evaluation-safeguard slice now: cohort metadata and per-cohort benchmark summaries.
