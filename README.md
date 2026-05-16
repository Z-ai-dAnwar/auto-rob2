# auto-rob2

Automated draft Cochrane Risk of Bias 2 (RoB 2) assessment for randomized controlled trial PDFs.

The pipeline uses a LangGraph state machine to orchestrate Docling-based PDF ingestion, ClinicalTrials.gov enrichment, outcome normalization, per-document local RAG retrieval, SQ-specific evidence packets, LLM signaling-question extraction, deterministic RoB 2 domain judgment algorithms, quote/packet verification, overall judgment, and Markdown/JSON reporting.

## Setup

Install dependencies with `uv`. The project expects Python `>=3.13`.

```bash
uv sync
```

PDF extraction and RAG use Docling, LangChain Docling, local `sentence-transformers` embeddings, and FAISS. The first embedding/tokenizer model download may require Hugging Face Hub auth; if needed, run `hf auth login` or set `HF_TOKEN` before the first assessment.

Create a local `.env` file:

```text
ROB2_PROVIDER=openrouter
OPENROUTER_API_KEY=your_key_here
# Optional alternatives when ROB2_PROVIDER changes:
# ANTHROPIC_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
```

Optional runtime settings:

- `ROB2_MODEL`, `ROB2_TEMPERATURE`, `ROB2_MAX_TOKENS`: model configuration.
- `ROB2_RPM_LIMIT`, `ROB2_RPD_LIMIT`: OpenRouter rate limits.
- `ROB2_EFFECT_OF_INTEREST`: default effect, `ITT` or `per-protocol`.
- `ROB2_USE_CACHE=1`: enable prompt cache in `.rob2_cache/`; `--no-cache` disables it for one CLI run.
- `ROB2_CTGOV_CACHE`: ClinicalTrials.gov API cache location.
- `ROB2_REMOTE_EVIDENCE_EXTRACTION=0`: skip the ingestion-time LLM evidence refinement and use Docling structural extraction only.

`.env` and generated `outputs/` are ignored by git, except `outputs/benchmark/`.

## Project I/O

Use this layout for local assessment runs:

```text
data/references/    # benchmark ground-truth CSVs
inputs/             # local PDFs to assess; PDFs are ignored by git
inputs/benchmark/   # benchmark PDFs (tracked by git)
outputs/            # generated reports and JSON data; ignored by git
outputs/benchmark/  # benchmark outputs (tracked by git)
```

Example local input path:

```text
inputs/example.pdf
```

## Run

```bash
uv run python main.py inputs/example.pdf --output-dir outputs
```

Assess a specific outcome or effect of interest:

```bash
uv run python main.py inputs/example.pdf --outcome "Functional Recovery" --effect ITT --output-dir outputs
```

Useful runtime flags:

- `--outcome`: specific outcome to assess; otherwise the preliminary node selects the primary outcome when possible.
- `--effect`: effect of interest, `ITT` or `per-protocol`; defaults to `ROB2_EFFECT_OF_INTEREST` or `ITT`.
- `--no-cache`: bypass the prompt cache for this run.
- `--debug`: print a compact state summary after each assessment.

Run every PDF in `inputs/`:

```bash
uv run python main.py inputs --output-dir outputs
```

Or call the Python API:

```python
from rob2_pipeline.pipeline import run_assessment

state = run_assessment(
    "inputs/example.pdf",
    outcome="Functional Recovery",
    effect_of_interest="ITT",
    output_dir="outputs",
)
```

Generated files:

- `outputs/<pdf_basename>_rob2_report.md`
- `outputs/<pdf_basename>_rob2_data.json`

The JSON output includes source and quality diagnostics for human review:

- `rag_sources`: retrieved chunk text, section labels, page numbers, and similarity scores by RoB 2 domain when vector retrieval succeeds.
- `retrieval_grades`: domain-level relevance/coverage grades and retry recommendations.
- `evidence_packets`, `evidence_facts`, and `packet_grades`: SQ-level evidence contracts, selected sources, candidate facts, missing-evidence flags, and packet retry recommendations.
- `evidence_validation_flags`, `verifier_trace`, and `verification_actions`: quote-support and packet-quality checks emitted before overall judgment.

## Benchmark

Run benchmark comparisons against reference RoB 2 judgments (defaults to `inputs/benchmark/`):

```bash
uv run python benchmark.py \
  --outcome-map CHAARTED:OS ARCHES:PFS PEACE-1:AE
```

Benchmark outcome codes are:

- `OS`: Overall Survival
- `PFS`: Progression-Free Survival
- `AE`: Adverse Events

Outcome-map entries can include an optional cohort label, useful for separating visible calibration runs from held-out validation runs:

```bash
uv run python benchmark.py \
  --outcome-map CHAARTED:OS:calibration ARCHES:PFS:validation PEACE-1:AE:validation
```

If no cohort label is provided, results store `unspecified` internally in JSON. Markdown reports hide the cohort table and column when all runs are unspecified.

Default reference CSV locations:

- `data/references/overall_survival.csv`
- `data/references/progression_free_survival.csv`
- `data/references/adverse_events.csv`

Validate configuration without running LLM calls:

```bash
uv run python benchmark.py \
  --outcome-map CHAARTED:OS ARCHES:PFS PEACE-1:AE \
  --dry-run
```

Benchmark outputs are written to the requested output directory as `benchmark_report.md`, `benchmark_results.json`, and per-trial assessment subdirectories such as `<TRIAL>_<outcome_code>/`.

## Architecture

- `rob2_pipeline/pdf_ingestion.py`: Docling PDF extraction, OCR retry, structural evidence extraction, optional LLM evidence refinement, section fallback parsing, and Docling chunk creation.
- `rob2_pipeline/docling_utils.py`: compatibility helpers for Docling labels and table export.
- `rob2_pipeline/rag.py`: local embedding, section-filtered FAISS indexing, adaptive retrieval over Docling chunks, and domain-level retrieval grading.
- `rob2_pipeline/rag_queries.py`: SQ-level retrieval query sets aggregated into domain-level RAG queries.
- `rob2_pipeline/methodology/`: canonical RoB 2 rule cards and renderer used by prompt templates.
- `rob2_pipeline/prompts.py`: prompt templates plus rendered canonical methodology blocks.
- `rob2_pipeline/providers/`: provider abstraction (`openrouter`, `anthropic`, `openai`) via LangChain integrations.
- `rob2_pipeline/config.py`: provider selection/env config and `build_provider()`.
- `rob2_pipeline/registration_api.py`: ClinicalTrials.gov API v2 fetch/extract/format helpers.
- `rob2_pipeline/nodes/`: LangGraph nodes, including outcome resolver, trial-fact extraction, evidence-packet building, domain SQ/judge nodes, quote verification, and reporting.
- `rob2_pipeline/judges/`: deterministic RoB 2 decision tables.
- `rob2_pipeline/graph.py`: LangGraph wiring with parallel domain fan-out after evidence-packet construction.
- `rob2_pipeline/nodes/rag_retrieval.py`: per-document retrieval context builder with evidence fallback, retrieval grading, and extra D3 censoring context.
- `rob2_pipeline/pipeline.py`: user-facing entry point and output writing.
- `rob2_pipeline/benchmark.py`: benchmark runner, comparison, summaries, and report writer.
- `tests/`: deterministic and mocked graph tests.

## Important Notes

LLMs answer the RCT screen, preliminary extraction, and signaling questions. Domain and overall judgments are computed by deterministic Python functions in `rob2_pipeline/judges/`.

Ingestion has two LLM touchpoints: the RCT screener always uses the configured provider after PDF evidence is extracted, and the optional paper-evidence refinement call can be disabled with `ROB2_REMOTE_EVIDENCE_EXTRACTION=0`. If Docling structural extraction or vector retrieval fails, the pipeline falls back to deterministic keyword-mapped evidence sections so the assessment can still proceed.

Evidence-packet and quote verification are quality gates for review triage; they flag unsupported quotes, missing required evidence, fragile D3/D5 reasoning, and packets that should be retried or escalated. The generated report remains a draft assessment for human verification, not a substitute for independent systematic-review judgment.
