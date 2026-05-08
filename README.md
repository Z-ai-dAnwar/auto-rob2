# auto-rob2

Automated draft Cochrane Risk of Bias 2 (RoB 2) assessment for randomized controlled trial PDFs.

The pipeline uses a LangGraph state machine to orchestrate PDF ingestion, LLM signaling-question extraction, deterministic RoB 2 domain judgment algorithms, overall judgment, and Markdown/JSON reporting.

## Setup

Install dependencies with `uv`:

```bash
uv sync
```

Create a local `.env` file:

```text
OPENROUTER_API_KEY=your_key_here
```

`.env` and generated `outputs/` are ignored by git.

## Project I/O

Use this layout for local assessment runs:

```text
data/references/  # benchmark ground-truth CSVs
inputs/           # local PDFs to assess; PDFs are ignored by git
outputs/          # generated reports and JSON data; ignored by git
```

The included local test article is organized as:

```text
inputs/NEJMoa1503747.pdf
```

## Run

```bash
uv run python main.py inputs/NEJMoa1503747.pdf --output-dir outputs
```

Run every PDF in `inputs/`:

```bash
uv run python main.py inputs --output-dir outputs
```

Or call the Python API:

```python
from rob2_pipeline.pipeline import run_assessment

state = run_assessment("inputs/NEJMoa1503747.pdf", output_dir="outputs")
```

Generated files:

- `outputs/<pdf_basename>_rob2_report.md`
- `outputs/<pdf_basename>_rob2_data.json`

## Benchmark

Run benchmark comparisons against reference RoB 2 judgments:

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
- `rob2_pipeline/prompts.py`: prompt constants.
- `rob2_pipeline/llm_client.py`: OpenRouter client, dotenv loading, retry, and proactive rate limiting.
- `rob2_pipeline/nodes/`: LangGraph nodes.
- `rob2_pipeline/judges/`: deterministic RoB 2 decision tables.
- `rob2_pipeline/graph.py`: sequential LangGraph wiring.
- `rob2_pipeline/pipeline.py`: user-facing entry point and output writing.
- `tests/`: deterministic and mocked graph tests.

## Important Notes

LLMs answer only signaling questions. Domain and overall judgments are computed by deterministic Python functions in `rob2_pipeline/judges/`.

The generated report is a draft assessment for human verification, not a substitute for independent systematic-review judgment.
