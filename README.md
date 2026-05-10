# auto-rob2

Automated draft Cochrane Risk of Bias 2 (RoB 2) assessment for randomized controlled trial PDFs.

The pipeline uses a LangGraph state machine to orchestrate PDF ingestion, per-document local RAG retrieval, LLM signaling-question extraction, deterministic RoB 2 domain judgment algorithms, overall judgment, and Markdown/JSON reporting.

## Setup

Install dependencies with `uv`:

```bash
uv sync
```

The RAG layer uses local embeddings and FAISS. The first model download may require Hugging Face Hub auth; if needed, run `hf auth login` or set `HF_TOKEN` before the first assessment.

Create a local `.env` file:

```text
ROB2_PROVIDER=openrouter
OPENROUTER_API_KEY=your_key_here
# Optional alternatives when ROB2_PROVIDER changes:
# ANTHROPIC_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
```

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

Run every PDF in `inputs/`:

```bash
uv run python main.py inputs --output-dir outputs
```

Or call the Python API:

```python
from rob2_pipeline.pipeline import run_assessment

state = run_assessment("inputs/example.pdf", output_dir="outputs")
```

Generated files:

- `outputs/<pdf_basename>_rob2_report.md`
- `outputs/<pdf_basename>_rob2_data.json`

## Benchmark

Run benchmark comparisons against reference RoB 2 judgments (defaults to `inputs/benchmark/`):

```bash
uv run python benchmark.py \
  --outcome-map CHAARTED:OS ARCHES:PFS PEACE-1:AE
```

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

## Architecture

- `rob2_pipeline/pdf_ingestion.py`: PyMuPDF text extraction and section parsing.
- `rob2_pipeline/rag.py`: local Docling chunking, embedding, and FAISS retrieval.
- `rob2_pipeline/prompts.py`: prompt constants.
- `rob2_pipeline/providers/`: provider abstraction (`openrouter`, `anthropic`, `openai`) via LangChain integrations.
- `rob2_pipeline/config.py`: provider selection/env config and `build_provider()`.
- `rob2_pipeline/registration_api.py`: ClinicalTrials.gov API v2 fetch/extract/format helpers.
- `rob2_pipeline/nodes/`: LangGraph nodes.
- `rob2_pipeline/judges/`: deterministic RoB 2 decision tables.
- `rob2_pipeline/graph.py`: sequential LangGraph wiring.
- `rob2_pipeline/nodes/rag_retrieval.py`: per-document retrieval context builder.
- `rob2_pipeline/pipeline.py`: user-facing entry point and output writing.
- `tests/`: deterministic and mocked graph tests.

## Important Notes

LLMs answer only signaling questions. Domain and overall judgments are computed by deterministic Python functions in `rob2_pipeline/judges/`.

The generated report is a draft assessment for human verification, not a substitute for independent systematic-review judgment.
