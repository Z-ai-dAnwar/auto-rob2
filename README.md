# auto-rob2

Automated first-pass Cochrane Risk of Bias 2 (RoB 2) assessment for randomized controlled trial PDFs.

`auto-rob2` runs a LangGraph workflow that extracts trial evidence from PDFs, enriches trial metadata from ClinicalTrials.gov when possible, retrieves domain-specific context with local embeddings and FAISS, asks LLMs to answer RoB 2 signaling questions, and then applies deterministic Python decision tables for domain and overall judgments. Outputs are draft Markdown reports plus JSON diagnostics for human review.

## Setup

Install dependencies with `uv`. The project expects Python `>=3.13`.

```bash
uv sync
```

PDF extraction and retrieval use Docling, LangChain Docling, the local Hugging Face embedding model `BAAI/bge-small-en-v1.5`, and FAISS. The first tokenizer/embedding download may require Hugging Face Hub auth; if needed, run `hf auth login` or set `HF_TOKEN` before the first assessment.

Create a local `.env` file for provider credentials:

```text
OPENROUTER_API_KEY=your_key_here
# Optional alternatives when ROB2_PROVIDER is exported as anthropic or openai:
# ANTHROPIC_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
```

Optional runtime settings:

- `ROB2_PROVIDER`: `openrouter` (default), `anthropic`, or `openai`.
- `ROB2_MODEL`, `ROB2_TEMPERATURE`, `ROB2_MAX_TOKENS`: model configuration.
- `ROB2_RPM_LIMIT`, `ROB2_RPD_LIMIT`: OpenRouter rate limits.
- `ROB2_EFFECT_OF_INTEREST`: default effect, `ITT` or `per-protocol`.
- `ROB2_USE_CACHE=1`: enable prompt cache in `.rob2_cache/`; `--no-cache` disables it for one CLI run.
- `ROB2_CTGOV_CACHE`: ClinicalTrials.gov API cache location.
- `ROB2_REMOTE_EVIDENCE_EXTRACTION=0`: skip the ingestion-time LLM evidence refinement and use Docling structural extraction only.

Settings such as `ROB2_PROVIDER`, `ROB2_MODEL`, and rate limits are read from the process environment during import. Export them before running the CLI if you need values other than the defaults; `.env` is still useful for API keys loaded when the provider is built.

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

For PDFs screened as non-RCTs, the graph stops after screening; JSON is still written, but there may be no Markdown report and the judgment fields remain unset.

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

- `rob2_pipeline/graph.py`: LangGraph wiring from ingestion through reporting, with early stop for non-RCTs and parallel D1-D5 fan-out after evidence packets are built.
- `rob2_pipeline/pdf_ingestion.py`: Docling markdown extraction, OCR retry, structural evidence extraction, optional LLM evidence refinement, fallback section parsing, censoring-context extraction, and Docling `HybridChunker` chunk creation.
- `rob2_pipeline/rag.py` and `rag_queries.py`: BGE-small embeddings, LangChain FAISS indexes, section-filtered adaptive retrieval, retrieval grading, and SQ-derived domain query sets.
- `rob2_pipeline/nodes/`: graph nodes for RCT screening, preliminary metadata, outcome normalization, trial facts, retrieval, evidence packets, signaling questions, deterministic judges, quote/packet verification, overall judgment, and report formatting.
- `rob2_pipeline/methodology/`, `prompts.py`, and `judges/`: canonical RoB 2 guidance, XML prompt templates, and deterministic domain/overall decision tables.
- `rob2_pipeline/providers/` and `config.py`: LangChain-backed provider abstraction for OpenRouter, Anthropic, and OpenAI.
- `rob2_pipeline/registration_api.py`: ClinicalTrials.gov API v2 enrichment and optional cache.
- `rob2_pipeline/pipeline.py`: public Python entry point and Markdown/JSON output writer.
- `rob2_pipeline/benchmark.py`: benchmark runner, comparison, cohort summaries, and benchmark report writer.
- `tests/`: mocked unit and graph tests for deterministic behavior.

## Important Notes

LLMs answer the RCT screen, preliminary extraction, optional ingestion evidence refinement, and signaling questions. Domain and overall judgments are computed by deterministic Python functions in `rob2_pipeline/judges/`.

If Docling structural extraction or vector retrieval fails after text extraction, the pipeline falls back to deterministic keyword-mapped evidence sections so the assessment can still proceed. If the RCT screener determines the paper is not an RCT, downstream RoB 2 assessment nodes do not run.

Evidence-packet and quote verification are quality gates for review triage; they flag unsupported quotes, missing required evidence, fragile D3/D5 reasoning, and packets that should be retried or escalated. The generated report remains a draft assessment for human verification, not a substitute for independent systematic-review judgment.
