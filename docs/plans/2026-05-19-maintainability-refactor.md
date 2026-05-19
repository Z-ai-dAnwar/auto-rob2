# Maintainability Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simplify the Python codebase while preserving current RoB 2 pipeline behavior, public entry points, and output schemas.

**Architecture:** Use a staged refactor with stable facades for active development. Move code by responsibility first, then simplify only where tests cover the behavior and the public import surface stays compatible.

**Tech Stack:** Python 3.13, uv, pytest, Ruff, LangGraph, LangChain Docling, Docling, Pydantic-style typed dictionaries.

---

## Reference Spec

- `docs/specs/2026-05-19-maintainability-refactor-design.md`

## File Structure

- Modify: `rob2_pipeline/providers/__init__.py`
  - Keep provider exports explicit and Ruff-clean.
- Modify: `tests/test_rate_limiter.py`
  - Remove unused test import.
- Create: `rob2_pipeline/ingestion/__init__.py`
  - Re-export ingestion helpers for the new internal package.
- Create: `rob2_pipeline/ingestion/settings.py`
  - Own section constants, Docling runtime constants, remote extraction flag, and RCT-candidate heuristic.
- Create: `rob2_pipeline/ingestion/docling_extract.py`
  - Own Docling conversion, full-text extraction, runtime configuration, chunk building, and Docling converter cache.
- Create: `rob2_pipeline/ingestion/document_repr.py`
  - Own `DocBlock`, `DocumentRepr`, Docling item traversal, page extraction, and markdown export.
- Create: `rob2_pipeline/ingestion/evidence.py`
  - Own paper-evidence prompt, XML parsing, LLM extraction, structural evidence mapping, section capping, section parsing, and censoring context.
- Modify: `rob2_pipeline/pdf_ingestion.py`
  - Become a compatibility facade that re-exports the existing public and test-used ingestion API.
- Create: `rob2_pipeline/nodes/evidence_contracts.py`
  - Own `EvidenceContract`, `CONTRACTS`, and packet regex/alias constants.
- Create: `rob2_pipeline/nodes/evidence_source_selection.py`
  - Own source collection, fallback section sources, term matching, and wrong-outcome detection.
- Create: `rob2_pipeline/nodes/evidence_packet_grading.py`
  - Own missing-evidence checks, negative flags, confidence scoring, packet grading, fact extraction, and text compaction.
- Modify: `rob2_pipeline/nodes/evidence_packets.py`
  - Keep `evidence_packet_builder_node`, `build_evidence_packets`, and `packet_block_for_domain` as stable imports while delegating helper logic to focused modules.
- Create: `rob2_pipeline/nodes/domain_helpers.py`
  - Own a narrow helper for calling SQ prompts with packet text and RAG sources.
- Modify: `rob2_pipeline/nodes/domain1.py`
  - Use the helper while preserving prompt content and SQ IDs.
- Modify: `rob2_pipeline/nodes/domain3.py`
  - Use the helper for the LLM call only; keep D3 NA branching explicit.
- Modify: `rob2_pipeline/nodes/domain5.py`
  - Use the helper for the LLM call only; keep Domain 5 error and review-priority behavior explicit.
- Modify: `ARCHITECTURE.md`
  - Update module responsibility descriptions after code moves.
- Test: `tests/test_pdf_ingestion.py`
  - Keep compatibility-import coverage and update monkeypatch targets where needed.
- Test: `tests/test_evidence_packets.py`
  - Keep packet behavior coverage and add import compatibility assertions.
- Test: `tests/test_domain_evidence_priority.py`
  - Keep domain prompt behavior coverage.

---

### Task 1: Hygiene Baseline

**Files:**
- Modify: `rob2_pipeline/providers/__init__.py`
- Modify: `tests/test_rate_limiter.py`

- [ ] **Step 1: Run the current lint check**

Run:

```bash
uv run ruff check .
```

Expected: FAIL with only the known unused import findings in `rob2_pipeline/providers/__init__.py` and `tests/test_rate_limiter.py`.

- [ ] **Step 2: Make provider re-export explicit**

Change `rob2_pipeline/providers/__init__.py` to:

```python
from .base import LLMProvider, LLMResponse as LLMResponse


def get_provider(provider_name: str, **kwargs) -> LLMProvider:
    if provider_name == "openrouter":
        from .openrouter import OpenRouterProvider

        return OpenRouterProvider(**kwargs)
    if provider_name == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider(**kwargs)
    if provider_name == "openai":
        from .openai import OpenAIProvider

        return OpenAIProvider(**kwargs)
    raise ValueError(f"Unsupported provider: {provider_name}")
```

- [ ] **Step 3: Remove the unused pytest import**

In `tests/test_rate_limiter.py`, remove only this line:

```python
import pytest
```

- [ ] **Step 4: Verify lint passes**

Run:

```bash
uv run ruff check .
```

Expected: PASS with `All checks passed!`.

- [ ] **Step 5: Run focused provider/rate-limiter tests**

Run:

```bash
uv run python -m pytest tests/test_rate_limiter.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit hygiene**

Run:

```bash
git add rob2_pipeline/providers/__init__.py tests/test_rate_limiter.py
git commit -m "Clean up lint baseline"
```

Expected: Commit succeeds.

---

### Task 2: Split Ingestion Without Behavior Changes

**Files:**
- Create: `rob2_pipeline/ingestion/__init__.py`
- Create: `rob2_pipeline/ingestion/settings.py`
- Create: `rob2_pipeline/ingestion/docling_extract.py`
- Create: `rob2_pipeline/ingestion/document_repr.py`
- Create: `rob2_pipeline/ingestion/evidence.py`
- Modify: `rob2_pipeline/pdf_ingestion.py`
- Modify: `tests/test_pdf_ingestion.py`

- [ ] **Step 1: Add compatibility tests for the facade**

Append these tests to `tests/test_pdf_ingestion.py`:

```python
def test_pdf_ingestion_facade_reexports_core_ingestion_api():
    assert callable(pdf_ingestion.extract_full_text)
    assert callable(pdf_ingestion.extract_paper_evidence)
    assert callable(pdf_ingestion.extract_structural_paper_evidence)
    assert callable(pdf_ingestion.parse_sections)
    assert callable(pdf_ingestion.extract_censoring_context)


def test_docling_chunker_can_still_be_monkeypatched_via_facade(monkeypatch):
    mock_conv = type("ConversionResult", (), {"document": object()})()
    mock_chunks = [_make_mock_chunk("Facade chunk.", ["Methods"], [5])]

    class MockChunker:
        def __init__(self, tokenizer):
            self.tokenizer = tokenizer

        def chunk(self, document):
            return mock_chunks

    monkeypatch.setattr(pdf_ingestion, "HybridChunker", MockChunker)

    result = pdf_ingestion._build_docling_chunks(mock_conv)

    assert result[0].page_content == "Facade chunk."
    assert result[0].metadata["page_numbers"] == [5]
```

- [ ] **Step 2: Run the new facade tests and confirm current behavior**

Run:

```bash
uv run python -m pytest tests/test_pdf_ingestion.py::test_pdf_ingestion_facade_reexports_core_ingestion_api tests/test_pdf_ingestion.py::test_docling_chunker_can_still_be_monkeypatched_via_facade -q
```

Expected: PASS before the move because the current monolithic module still owns these symbols.

- [ ] **Step 3: Create `rob2_pipeline/ingestion/settings.py`**

Move constants and simple settings helpers from `rob2_pipeline/pdf_ingestion.py` into `rob2_pipeline/ingestion/settings.py` with this content shape:

```python
import os
import re

SECTION_PATTERNS = {
    "abstract": ["abstract"],
    "methods": [
        "methods",
        "materials and methods",
        "patients and methods",
        "study design",
        "methodology",
    ],
    "randomization": [
        "randomis",
        "randomiz",
        "random allocation",
        "allocation sequence",
        "sequence generation",
    ],
    "blinding": ["blind", "mask", "open-label", "open label", "double-blind"],
    "outcomes": [
        "outcome",
        "endpoint",
        "primary outcome",
        "secondary outcome",
        "efficacy measure",
    ],
    "analysis": [
        "statistical analysis",
        "statistical methods",
        "data analysis",
        "intention-to-treat",
        "per-protocol",
        "analysis population",
    ],
    "results": ["results", "findings"],
    "missing_data": [
        "missing data",
        "lost to follow",
        "dropout",
        "withdrawal",
        "discontinu",
    ],
    "registration": [
        "clinicaltrials",
        "isrctn",
        "trial registration",
        "registered",
        "protocol number",
    ],
    "baseline": ["baseline", "demographic", "characteristics"],
    "consort": [
        "consort",
        "flow diagram",
        "figure 1",
        "participant flow",
        "screened",
        "enrolled",
        "randomized",
        "allocated",
    ],
    "supplementary": ["supplement", "appendix", "online material"],
}

SECTION_ORDER = list(SECTION_PATTERNS)
MAX_SECTION_CHARS = 10000
MIN_EXTRACTED_CHARS = 20
EMBED_MODEL_ID = "BAAI/bge-small-en-v1.5"
EMBED_MAX_TOKENS = 256
TOKENIZER_COUNTING_MAX_LENGTH = 10**9
CENSORING_PATTERNS = [
    re.compile(r"(?i)\bcensor\w*\b.*\d|\d.*\bcensor\w*\b"),
    re.compile(r"(?i)\bdata[ -]?maturity\b.*\d|\d\s*%\s*data\s*maturity"),
    re.compile(r"(?i)\bdata[ -]?cut(?:off)?\b.*\d|\d.*\bdata[ -]?cut(?:off)?\b"),
    re.compile(
        r"(?i)\bfollow[ -]?up\b.*\bcomplete\b.*\d|\d.*\bfollow[ -]?up\b.*\bcomplete\b"
    ),
    re.compile(r"(?i)\badministratively\s+censored\b"),
    re.compile(r"(?i)\bmedian\s+follow[ -]?up\b.*\d"),
    re.compile(r"(?i)\b\d[\d,]*\s*/\s*\d[\d,]*\s+participants?\b.*\bevents?\b"),
    re.compile(r"(?i)\b\d[\d,]*\s+events?\b.*\d|\d.*\b\d[\d,]*\s+events?\b"),
]


def allow_remote_evidence_extraction() -> bool:
    return os.getenv("ROB2_REMOTE_EVIDENCE_EXTRACTION", "1").strip() not in {
        "0",
        "false",
        "False",
    }


def appears_rct_candidate(text: str) -> bool:
    lowered = text.lower()
    trial_signals = [
        "random",
        "randomized",
        "randomised",
        "assigned",
        "allocation",
        "placebo",
        "double-blind",
    ]
    context_signals = ["trial", "participants", "patients", "phase "]
    return any(signal in lowered for signal in trial_signals) and any(
        signal in lowered for signal in context_signals
    )
```

- [ ] **Step 4: Create `rob2_pipeline/ingestion/docling_extract.py`**

Move Docling extraction and chunking helpers into `docling_extract.py`. Preserve names for compatibility:

```python
import logging
import os
import re

from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from langchain_core.documents import Document

from rob2_pipeline.ingestion.settings import (
    EMBED_MAX_TOKENS,
    EMBED_MODEL_ID,
    MIN_EXTRACTED_CHARS,
    TOKENIZER_COUNTING_MAX_LENGTH,
)

DOCLING_CONVERTERS: dict[bool, object] = {}


def extract_full_text(pdf_path: str) -> str:
    return _normalize_extracted_text(_extract_with_docling(pdf_path))


def _extract_with_docling(pdf_path: str) -> str:
    errors = []
    for use_ocr in (False, True):
        try:
            return _extract_with_docling_loader(pdf_path, use_ocr=use_ocr)
        except Exception as error:
            errors.append(f"OCR={use_ocr}: {error}")
    raise RuntimeError("; ".join(errors))


def _extract_with_docling_loader(pdf_path: str, use_ocr: bool) -> str:
    _configure_docling_runtime()

    from langchain_docling import DoclingLoader
    from langchain_docling.loader import ExportType

    loader = DoclingLoader(
        file_path=pdf_path,
        converter=_get_docling_converter(use_ocr=use_ocr),
        export_type=ExportType.MARKDOWN,
    )
    docs = list(loader.lazy_load())
    markdown = "\n\n".join(doc.page_content for doc in docs if doc.page_content)
    if len(markdown.strip()) < MIN_EXTRACTED_CHARS:
        raise RuntimeError(
            f"langchain-docling returned too little text to use with OCR={use_ocr}"
        )
    return markdown


def _get_docling_converter(use_ocr: bool):
    converter = DOCLING_CONVERTERS.get(use_ocr)
    if converter is not None:
        return converter

    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pipeline_options = PdfPipelineOptions()
    pipeline_options.allow_external_plugins = True
    pipeline_options.do_ocr = use_ocr
    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        },
    )
    DOCLING_CONVERTERS[use_ocr] = converter
    return converter


def _configure_docling_runtime() -> None:
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TQDM_DISABLE", "1")
    logging.getLogger("RapidOCR").setLevel(logging.WARNING)
    logging.getLogger("rapidocr").setLevel(logging.WARNING)


def _normalize_extracted_text(text: str) -> str:
    text = text.replace("\x00", "").replace("\xa0", " ")
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def _build_docling_chunker() -> HybridChunker:
    tokenizer = HuggingFaceTokenizer.from_pretrained(
        EMBED_MODEL_ID,
        max_tokens=EMBED_MAX_TOKENS,
        model_max_length=TOKENIZER_COUNTING_MAX_LENGTH,
    )
    return HybridChunker(tokenizer=tokenizer)


def _build_docling_chunks(conv_result) -> list[Document]:
    chunker = _build_docling_chunker()
    docs: list[Document] = []
    for chunk in chunker.chunk(conv_result.document):
        page_numbers = _chunk_page_numbers(chunk)
        docs.append(
            Document(
                page_content=chunk.text,
                metadata={
                    "section": chunk.meta.headings[0] if chunk.meta.headings else "",
                    "page_numbers": page_numbers,
                    "dl_meta": chunk.meta.export_json_dict(),
                },
            )
        )
    return docs


def _chunk_page_numbers(chunk) -> list[int]:
    direct_pages = getattr(chunk.meta, "page_numbers", None)
    if direct_pages is not None:
        return list(direct_pages)
    pages = set()
    for item in getattr(chunk.meta, "doc_items", []) or []:
        for prov in getattr(item, "prov", []) or []:
            page_no = getattr(prov, "page_no", None)
            if page_no:
                pages.add(int(page_no))
    return sorted(pages)
```

- [ ] **Step 5: Create `rob2_pipeline/ingestion/document_repr.py`**

Move document representation helpers into `document_repr.py`:

```python
from dataclasses import dataclass

from rob2_pipeline.docling_utils import export_table_markdown, label_name


@dataclass
class DocBlock:
    heading: str | None
    level: int
    text: str
    tables: list[str]
    page_start: int


@dataclass
class DocumentRepr:
    blocks: list[DocBlock]
    full_text: str

    def to_prompt_repr(self) -> str:
        parts = []
        for block in self.blocks:
            heading = block.heading or "Document"
            level = max(1, min(block.level or 1, 6))
            section_parts = [f"{'#' * level} {heading}"]
            if block.text.strip():
                section_parts.append(block.text.strip())
            for table in block.tables:
                if table.strip():
                    section_parts.append(f"[TABLE]\n{table.strip()}\n[/TABLE]")
            parts.append("\n\n".join(section_parts))
        return "\n\n".join(parts) if parts else self.full_text


def _page_no(item) -> int:
    prov = getattr(item, "prov", None) or []
    if prov:
        return int(getattr(prov[0], "page_no", 0) or 0)
    return 0


def _export_doc_markdown(doc) -> str:
    if hasattr(doc, "export_to_markdown"):
        return (doc.export_to_markdown() or "").strip()
    if hasattr(doc, "export_to_text"):
        return (doc.export_to_text() or "").strip()
    return ""


def build_document_repr(doc) -> DocumentRepr:
    blocks: list[DocBlock] = []
    current_heading: str | None = None
    current_level = 0
    current_text: list[str] = []
    current_tables: list[str] = []
    current_page = 0

    def flush() -> None:
        nonlocal current_text, current_tables, current_page
        text = "\n".join(part for part in current_text if part).strip()
        if text or current_tables:
            blocks.append(
                DocBlock(
                    heading=current_heading,
                    level=current_level,
                    text=text,
                    tables=list(current_tables),
                    page_start=current_page,
                )
            )
        current_text = []
        current_tables = []
        current_page = 0

    iterator = doc.iterate_items() if hasattr(doc, "iterate_items") else []
    for item, level in iterator:
        item_label_name = label_name(item)
        item_text = (getattr(item, "text", "") or "").strip()
        if item_label_name == "SECTION_HEADER":
            flush()
            current_heading = item_text or None
            current_level = int(level or 1)
            current_page = _page_no(item)
            continue
        if not current_page:
            current_page = _page_no(item)
        if item_label_name == "TABLE":
            table = export_table_markdown(item, doc)
            if table:
                current_tables.append(table)
            continue
        if (
            item_label_name
            in {"TEXT", "PARAGRAPH", "LIST_ITEM", "TITLE", "CAPTION", "FOOTNOTE"}
            and item_text
        ):
            current_text.append(item_text)

    flush()
    return DocumentRepr(blocks=blocks, full_text=_export_doc_markdown(doc))
```

- [ ] **Step 6: Create `rob2_pipeline/ingestion/evidence.py`**

Move the remaining evidence, section, and censoring helpers into `evidence.py`. Import `DocumentRepr` and settings from the new modules. Preserve the current function names:

```python
import logging
import re
import time
from typing import cast

from lxml import etree  # type: ignore[import-untyped]

from rob2_pipeline.config import build_provider
from rob2_pipeline.ingestion.document_repr import DocumentRepr
from rob2_pipeline.ingestion.settings import (
    CENSORING_PATTERNS,
    MAX_SECTION_CHARS,
    SECTION_ORDER,
    SECTION_PATTERNS,
)
from rob2_pipeline.models import (
    EVIDENCE_SECTION_FIELDS,
    PaperEvidence,
    empty_paper_evidence,
)
from rob2_pipeline.trace import append_llm_call
from rob2_pipeline.types import LLMCallLogEntry
from rob2_pipeline.xml_parser import sanitize_stray_lt
```

Then move these functions unchanged except for imports:

```python
_tables_from_xml
_parse_paper_evidence_response
extract_paper_evidence
paper_evidence_from_sections
extract_structural_paper_evidence
cap_section
_normalize_heading
_detect_heading
_extract_keyword_context
_augment_consort_from_results
_parse_sections_from_docling_document
extract_censoring_context
parse_sections
```

Keep the exact `PROMPT_PAPER_EXTRACTION` and `PAPER_EXTRACTION_SYSTEM_MESSAGE` text from the current module.

- [ ] **Step 7: Create `rob2_pipeline/ingestion/__init__.py`**

Use explicit re-exports:

```python
from rob2_pipeline.ingestion.docling_extract import (
    HybridChunker,
    HuggingFaceTokenizer,
    _build_docling_chunks,
    _build_docling_chunker,
    _chunk_page_numbers,
    _configure_docling_runtime,
    _extract_with_docling,
    _extract_with_docling_loader,
    _get_docling_converter,
    _normalize_extracted_text,
    extract_full_text,
)
from rob2_pipeline.ingestion.document_repr import (
    DocBlock,
    DocumentRepr,
    _export_doc_markdown,
    _page_no,
    build_document_repr,
)
from rob2_pipeline.ingestion.evidence import (
    PAPER_EXTRACTION_SYSTEM_MESSAGE,
    PROMPT_PAPER_EXTRACTION,
    _augment_consort_from_results,
    _detect_heading,
    _extract_keyword_context,
    _parse_paper_evidence_response,
    _parse_sections_from_docling_document,
    _tables_from_xml,
    cap_section,
    extract_censoring_context,
    extract_paper_evidence,
    extract_structural_paper_evidence,
    paper_evidence_from_sections,
    parse_sections,
)
from rob2_pipeline.ingestion.settings import (
    CENSORING_PATTERNS,
    EMBED_MAX_TOKENS,
    EMBED_MODEL_ID,
    MAX_SECTION_CHARS,
    MIN_EXTRACTED_CHARS,
    SECTION_ORDER,
    SECTION_PATTERNS,
    TOKENIZER_COUNTING_MAX_LENGTH,
    allow_remote_evidence_extraction,
    appears_rct_candidate,
)
```

- [ ] **Step 8: Replace `rob2_pipeline/pdf_ingestion.py` with a facade**

Keep monkeypatch compatibility for test-used symbols by making `extract_full_text` read facade-level `_extract_with_docling` and `_build_docling_chunker` read facade-level `HybridChunker` and `HuggingFaceTokenizer`:

```python
from langchain_core.documents import Document

from rob2_pipeline.ingestion import docling_extract as _docling_extract
from rob2_pipeline.ingestion.document_repr import (
    DocBlock,
    DocumentRepr,
    _export_doc_markdown,
    _page_no,
    build_document_repr,
)
from rob2_pipeline.ingestion.evidence import (
    PAPER_EXTRACTION_SYSTEM_MESSAGE,
    PROMPT_PAPER_EXTRACTION,
    _augment_consort_from_results,
    _detect_heading,
    _extract_keyword_context,
    _parse_paper_evidence_response,
    _parse_sections_from_docling_document,
    _tables_from_xml,
    cap_section,
    extract_censoring_context,
    extract_paper_evidence,
    extract_structural_paper_evidence,
    paper_evidence_from_sections,
    parse_sections,
)
from rob2_pipeline.ingestion.settings import (
    CENSORING_PATTERNS,
    EMBED_MAX_TOKENS,
    EMBED_MODEL_ID,
    MAX_SECTION_CHARS,
    MIN_EXTRACTED_CHARS,
    SECTION_ORDER,
    SECTION_PATTERNS,
    TOKENIZER_COUNTING_MAX_LENGTH,
    allow_remote_evidence_extraction,
    appears_rct_candidate,
)

HybridChunker = _docling_extract.HybridChunker
HuggingFaceTokenizer = _docling_extract.HuggingFaceTokenizer


def extract_full_text(pdf_path: str) -> str:
    return _normalize_extracted_text(_extract_with_docling(pdf_path))


def _extract_with_docling(pdf_path: str) -> str:
    return _docling_extract._extract_with_docling(pdf_path)


def _extract_with_docling_loader(pdf_path: str, use_ocr: bool) -> str:
    return _docling_extract._extract_with_docling_loader(pdf_path, use_ocr)


def _get_docling_converter(use_ocr: bool):
    return _docling_extract._get_docling_converter(use_ocr)


def _configure_docling_runtime() -> None:
    return _docling_extract._configure_docling_runtime()


def _normalize_extracted_text(text: str) -> str:
    return _docling_extract._normalize_extracted_text(text)


def _build_docling_chunker():
    tokenizer = HuggingFaceTokenizer.from_pretrained(
        EMBED_MODEL_ID,
        max_tokens=EMBED_MAX_TOKENS,
        model_max_length=TOKENIZER_COUNTING_MAX_LENGTH,
    )
    return HybridChunker(tokenizer=tokenizer)


def _build_docling_chunks(conv_result) -> list[Document]:
    chunker = _build_docling_chunker()
    docs: list[Document] = []
    for chunk in chunker.chunk(conv_result.document):
        page_numbers = _docling_extract._chunk_page_numbers(chunk)
        docs.append(
            Document(
                page_content=chunk.text,
                metadata={
                    "section": chunk.meta.headings[0] if chunk.meta.headings else "",
                    "page_numbers": page_numbers,
                    "dl_meta": chunk.meta.export_json_dict(),
                },
            )
        )
    return docs


def _chunk_page_numbers(chunk) -> list[int]:
    return _docling_extract._chunk_page_numbers(chunk)
```

- [ ] **Step 9: Run ingestion tests**

Run:

```bash
uv run python -m pytest tests/test_pdf_ingestion.py tests/test_domain_evidence_priority.py -q
```

Expected: PASS.

- [ ] **Step 10: Run graph tests that import ingestion**

Run:

```bash
uv run python -m pytest tests/test_graph.py tests/test_rag_retrieval_node.py -q
```

Expected: PASS.

- [ ] **Step 11: Run lint**

Run:

```bash
uv run ruff check rob2_pipeline/ingestion rob2_pipeline/pdf_ingestion.py tests/test_pdf_ingestion.py
```

Expected: PASS.

- [ ] **Step 12: Commit ingestion split**

Run:

```bash
git add rob2_pipeline/ingestion rob2_pipeline/pdf_ingestion.py tests/test_pdf_ingestion.py
git commit -m "Split PDF ingestion responsibilities"
```

Expected: Commit succeeds.

---

### Task 3: Split Evidence Packet Construction

**Files:**
- Create: `rob2_pipeline/nodes/evidence_contracts.py`
- Create: `rob2_pipeline/nodes/evidence_source_selection.py`
- Create: `rob2_pipeline/nodes/evidence_packet_grading.py`
- Modify: `rob2_pipeline/nodes/evidence_packets.py`
- Modify: `tests/test_evidence_packets.py`

- [ ] **Step 1: Add compatibility tests for packet imports**

Append this test to `tests/test_evidence_packets.py`:

```python
def test_evidence_packets_module_keeps_stable_public_api():
    from rob2_pipeline.nodes import evidence_packets

    assert callable(evidence_packets.evidence_packet_builder_node)
    assert callable(evidence_packets.build_evidence_packets)
    assert callable(evidence_packets.packet_block_for_domain)
```

- [ ] **Step 2: Run the compatibility test before moving code**

Run:

```bash
uv run python -m pytest tests/test_evidence_packets.py::test_evidence_packets_module_keeps_stable_public_api -q
```

Expected: PASS.

- [ ] **Step 3: Create `rob2_pipeline/nodes/evidence_contracts.py`**

Move `EvidenceContract`, `CONTRACTS`, `_RESULT_STAT_RE`, `_DENOMINATOR_RE`, `_SENTENCE_SPLIT_RE`, `_PRESPEC_TERMS`, and `_OUTCOME_ALIASES` into the new file. Rename the constants while moving so the new helper modules import non-private names: `RESULT_STAT_RE`, `DENOMINATOR_RE`, `SENTENCE_SPLIT_RE`, `PRESPEC_TERMS`, and `OUTCOME_ALIASES`. Preserve the existing contract definitions and regex values exactly. The top of the file should be:

```python
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceContract:
    sq_id: str
    domain: str
    required_evidence: tuple[str, ...]
    terms: tuple[str, ...]
    fallback_sections: tuple[str, ...] = ()
    needs_denominator: bool = False
    outcome_bound: bool = False
    needs_prespecification: bool = False
```

- [ ] **Step 4: Create `rob2_pipeline/nodes/evidence_source_selection.py`**

Move candidate-source helpers into the new file with these imports:

```python
import re

from rob2_pipeline.models import format_evidence
from rob2_pipeline.nodes.evidence_contracts import EvidenceContract, OUTCOME_ALIASES
from rob2_pipeline.rag_queries import SQ_QUERIES
from rob2_pipeline.state import RoB2State
from rob2_pipeline.types import PacketSource
```

Preserve these function names:

```python
candidate_sources
fallback_sources
contract_terms
matched_terms
looks_like_wrong_outcome
aliases_for_outcome
```

When moving, drop only the leading underscore from each function name. Keep the logic unchanged.

- [ ] **Step 5: Create `rob2_pipeline/nodes/evidence_packet_grading.py`**

Move grading and fact helpers into the new file with these imports:

```python
import re

from rob2_pipeline.nodes.evidence_contracts import (
    DENOMINATOR_RE,
    PRESPEC_TERMS,
    RESULT_STAT_RE,
    SENTENCE_SPLIT_RE,
    EvidenceContract,
)
from rob2_pipeline.nodes.evidence_source_selection import (
    contract_terms,
    looks_like_wrong_outcome,
)
from rob2_pipeline.state import RoB2State
from rob2_pipeline.types import EvidenceFact, PacketSource, RetrievalGrade
```

Preserve these function names:

```python
missing_evidence
negative_flags
confidence
grade_packet
source_to_fact
best_sentence
compact
```

When moving, drop only the leading underscore from each function name. Keep the logic unchanged.

- [ ] **Step 6: Rewrite `rob2_pipeline/nodes/evidence_packets.py` as orchestration**

Keep this file focused on public node behavior and packet rendering:

```python
"""Build small, SQ-specific evidence packets from retrieved source chunks."""

from __future__ import annotations

from rob2_pipeline.nodes.evidence_contracts import CONTRACTS, EvidenceContract
from rob2_pipeline.nodes.evidence_packet_grading import (
    compact,
    confidence,
    grade_packet,
    missing_evidence,
    negative_flags,
    source_to_fact,
)
from rob2_pipeline.nodes.evidence_source_selection import candidate_sources
from rob2_pipeline.state import RoB2State
from rob2_pipeline.types import EvidenceFact, EvidencePacket, RetrievalGrade


def evidence_packet_builder_node(state: RoB2State) -> RoB2State:
    return build_evidence_packets(state)
```

Keep `build_evidence_packets`, `packet_block_for_domain`, and `_build_packet_for_contract` in this file, updating helper calls to the new public helper names.

- [ ] **Step 7: Run packet tests**

Run:

```bash
uv run python -m pytest tests/test_evidence_packets.py tests/test_evidence_packet_prompting.py tests/test_verification.py -q
```

Expected: PASS.

- [ ] **Step 8: Run lint for packet modules**

Run:

```bash
uv run ruff check rob2_pipeline/nodes/evidence_packets.py rob2_pipeline/nodes/evidence_contracts.py rob2_pipeline/nodes/evidence_source_selection.py rob2_pipeline/nodes/evidence_packet_grading.py tests/test_evidence_packets.py
```

Expected: PASS.

- [ ] **Step 9: Commit packet split**

Run:

```bash
git add rob2_pipeline/nodes/evidence_packets.py rob2_pipeline/nodes/evidence_contracts.py rob2_pipeline/nodes/evidence_source_selection.py rob2_pipeline/nodes/evidence_packet_grading.py tests/test_evidence_packets.py
git commit -m "Split evidence packet construction"
```

Expected: Commit succeeds.

---

### Task 4: Keep Domain Node Simplification Narrow

**Files:**
- Create: `rob2_pipeline/nodes/domain_helpers.py`
- Modify: `rob2_pipeline/nodes/domain1.py`
- Modify: `rob2_pipeline/nodes/domain3.py`
- Modify: `rob2_pipeline/nodes/domain5.py`
- Test: `tests/test_domain_evidence_priority.py`

- [ ] **Step 1: Add a prompt-preservation regression test for D1**

Append this assertion to `test_domain1_keeps_structured_evidence_when_rag_context_exists` in `tests/test_domain_evidence_priority.py`:

```python
    assert "SQ 1.1" not in captured["prompt"] or "verified evidence packet" in captured["prompt"]
```

This keeps the test tolerant of empty packet text while still confirming packet text format if packets are present.

- [ ] **Step 2: Create `rob2_pipeline/nodes/domain_helpers.py`**

Add one helper that only centralizes the repeated LLM call pattern:

```python
from collections.abc import Callable

from rob2_pipeline.nodes.common import (
    call_node_llm,
    call_node_llm_with_sources,
    format_chunk_sources,
    merge_sq_answers,
)
from rob2_pipeline.state import RoB2State
from rob2_pipeline.xml_parser import parse_sq_response


def call_domain_sq_prompt(
    state: RoB2State,
    prompt: str,
    *,
    node_name: str,
    sq_ids: list[str],
    source_domain: str,
    parse_fn: Callable = parse_sq_response,
) -> tuple[dict[str, dict], list[dict]]:
    _response, log, parsed = call_node_llm_with_sources(
        call_node_llm,
        state,
        prompt,
        node_name,
        parse_fn,
        sq_ids,
        chunk_sources=format_chunk_sources(state, source_domain),
    )
    return merge_sq_answers(state, parsed or {}), log
```

- [ ] **Step 3: Use the helper in `domain1.py`**

Replace the `call_node_llm_with_sources(...)` block in `domain1_sq_node` with:

```python
    sq_answers, log = call_domain_sq_prompt(
        state,
        prompt,
        node_name="domain1_sq",
        sq_ids=["1.1", "1.2", "1.3"],
        source_domain="d1",
    )
```

Update imports so `domain1.py` imports `call_domain_sq_prompt` and no longer imports `call_node_llm`, `call_node_llm_with_sources`, `format_chunk_sources`, `merge_sq_answers`, or `parse_sq_response`.

- [ ] **Step 4: Use the helper in `domain3.py`**

Replace only the LLM-call block in `domain3_sq_node` with:

```python
    sq_answers, log = call_domain_sq_prompt(
        state,
        prompt,
        node_name="domain3_sq",
        sq_ids=["3.1", "3.2", "3.3", "3.4"],
        source_domain="d3",
    )
```

Keep the D3 `set_na(...)` branching exactly where it is today. Update imports so D3 keeps `set_na` but drops the duplicated LLM-call imports.

- [ ] **Step 5: Use the helper in `domain5.py`**

Replace only the LLM-call block in `domain5_sq_node` with:

```python
    sq_answers, log = call_domain_sq_prompt(
        state,
        prompt,
        node_name="domain5_sq",
        sq_ids=["5.1", "5.2", "5.3"],
        source_domain="d5",
    )
```

Keep Domain 5 error collection and `human_review_priority` behavior explicit in `domain5.py`. Update imports to remove duplicated LLM-call imports.

- [ ] **Step 6: Run domain-node tests**

Run:

```bash
uv run python -m pytest tests/test_domain_evidence_priority.py tests/test_graph.py tests/test_judges.py -q
```

Expected: PASS.

- [ ] **Step 7: Run lint for domain nodes**

Run:

```bash
uv run ruff check rob2_pipeline/nodes/domain_helpers.py rob2_pipeline/nodes/domain1.py rob2_pipeline/nodes/domain3.py rob2_pipeline/nodes/domain5.py tests/test_domain_evidence_priority.py
```

Expected: PASS.

- [ ] **Step 8: Commit domain helper**

Run:

```bash
git add rob2_pipeline/nodes/domain_helpers.py rob2_pipeline/nodes/domain1.py rob2_pipeline/nodes/domain3.py rob2_pipeline/nodes/domain5.py tests/test_domain_evidence_priority.py
git commit -m "Share simple domain SQ call helper"
```

Expected: Commit succeeds.

---

### Task 5: Documentation and Full Verification

**Files:**
- Modify: `ARCHITECTURE.md`
- Modify: `README.md` only if public usage text changes during implementation

- [ ] **Step 1: Update architecture module descriptions**

In `ARCHITECTURE.md`, update the `rob2_pipeline/pdf_ingestion.py` bullet to describe the facade and new ingestion package:

```markdown
- `rob2_pipeline/pdf_ingestion.py`
  - Compatibility facade for ingestion helpers used by graph nodes and tests.
  - Re-exports focused modules under `rob2_pipeline/ingestion/`.

- `rob2_pipeline/ingestion/`
  - `docling_extract.py`: Docling text extraction, OCR retry, converter caching, and chunk creation.
  - `document_repr.py`: Docling item traversal and prompt-facing document representation.
  - `evidence.py`: paper evidence extraction, structural section mapping, keyword fallbacks, and censoring context.
  - `settings.py`: ingestion constants and runtime feature flags.
```

- [ ] **Step 2: Update evidence-packet architecture text**

In `ARCHITECTURE.md`, update the `nodes/evidence_packets.py` description to:

```markdown
- `rob2_pipeline/nodes/evidence_packets.py`
  - Orchestrates SQ-level packet construction and prompt-facing packet rendering.
  - Contract definitions, source selection, and packet grading live in focused sibling modules.
```

- [ ] **Step 3: Run the full test suite**

Run:

```bash
uv run python -m pytest -q
```

Expected: PASS.

- [ ] **Step 4: Run full lint**

Run:

```bash
uv run ruff check .
```

Expected: PASS with `All checks passed!`.

- [ ] **Step 5: Run import smoke checks**

Run:

```bash
uv run python -c "from rob2_pipeline.pipeline import run_assessment; from rob2_pipeline.pdf_ingestion import extract_full_text, parse_sections; from rob2_pipeline.nodes.evidence_packets import build_evidence_packets, packet_block_for_domain; print('imports ok')"
```

Expected: prints `imports ok`.

- [ ] **Step 6: Commit docs and verification updates**

Run:

```bash
git add ARCHITECTURE.md README.md
git commit -m "Document maintainability refactor structure"
```

Expected: Commit succeeds if documentation changed. If `README.md` did not change, omit it from `git add`.

---

## Final Acceptance

- [ ] `uv run python -m pytest -q` passes.
- [ ] `uv run ruff check .` passes.
- [ ] `rob2_pipeline.pdf_ingestion` still exports the ingestion functions used by existing tests and nodes.
- [ ] `rob2_pipeline.nodes.evidence_packets` still exports `evidence_packet_builder_node`, `build_evidence_packets`, and `packet_block_for_domain`.
- [ ] No prompt text, judge decision table, CLI argument, environment variable, JSON schema, or Markdown report schema changed.
- [ ] `ARCHITECTURE.md` reflects new module boundaries.
