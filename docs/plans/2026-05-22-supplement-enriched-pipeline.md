# Supplement-Enriched Evidence Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional supplementary PDF ingestion so protocols, appendices, SAP-like files, and ClinicalTrials.gov evidence can enrich RoB 2 evidence packets without changing primary-only behavior.

**Architecture:** Keep the primary article as the authoritative `full_text` and `PaperEvidence` source. Parse optional supplements through the existing Docling chunk path, append provenance-tagged chunks to `docling_chunks`, preserve provenance through RAG metadata and packet rendering, and use lightweight source-role ranking for RoB 2 packet selection.

**Tech Stack:** Python 3.12, LangGraph state reducers, Docling chunk conversion helpers, LangChain `Document`, LangChain FAISS retrieval, pytest, existing provider and benchmark CLIs.

**Spec:** `docs/specs/2026-05-22-supplement-enriched-pipeline-design.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `rob2_pipeline/types.py` | Modify | Add `SourceDocument`; extend `ChunkMeta`, `PacketSource`, and `EvidenceFact` provenance fields |
| `rob2_pipeline/state.py` | Modify | Add supplement-related state channels |
| `rob2_pipeline/state_factory.py` | Modify | Initialize supplement state |
| `rob2_pipeline/ingestion/docling_extract.py` | Modify | Let chunk building accept source metadata |
| `rob2_pipeline/ingestion/supplements.py` | Create | Supplement classification, source document records, metadata application, ingestion |
| `rob2_pipeline/nodes/ingest.py` | Modify | Ingest optional supplements after primary PDF chunking |
| `rob2_pipeline/rag.py` | Modify | Preserve provenance metadata and include `document_id` in dedupe key |
| `rob2_pipeline/nodes/rag_retrieval.py` | Modify | Return provenance-rich `rag_chunk_metadata` unchanged |
| `rob2_pipeline/nodes/evidence_source_selection.py` | Modify | Add CT.gov sources and source-role ranking fields |
| `rob2_pipeline/nodes/evidence_packet_grading.py` | Modify | Keep provenance when converting sources to facts; page-warning exemptions |
| `rob2_pipeline/nodes/evidence_packets.py` | Modify | Render document name, role, page, and section in packet blocks |
| `rob2_pipeline/pipeline.py` | Modify | Accept `supplementary_paths`; emit supplement JSON fields |
| `main.py` | Modify | Add `--supplement` and `--supplement-dir` |
| `rob2_pipeline/benchmark.py` | Modify | Add supplement discovery and benchmark API options |
| `benchmark.py` | Modify | Add benchmark CLI flags and dry-run output |
| `tests/test_types.py` | Modify | Type shape tests |
| `tests/test_supplements.py` | Create | Supplement classification, metadata, and ingestion helper tests |
| `tests/test_rag.py` | Modify | `_doc_key` and metadata propagation tests |
| `tests/test_rag_retrieval_node.py` | Modify | Provenance preservation tests |
| `tests/test_evidence_packets.py` | Modify | Packet rendering and CT.gov source tests |
| `tests/test_verification.py` | Modify | Missing-page exemption tests |
| `tests/test_benchmark.py` | Modify | Supplement discovery and benchmark behavior tests |
| `tests/test_pipeline.py` or existing pipeline test file | Modify | `run_assessment` state initialization/output test |

---

## Task 1: Add Source Types And State Fields

**Files:**
- Modify: `rob2_pipeline/types.py`
- Modify: `rob2_pipeline/state.py`
- Modify: `rob2_pipeline/state_factory.py`
- Test: `tests/test_types.py`

- [ ] **Step 1: Write failing type tests**

Add these tests to `tests/test_types.py`:

```python
from rob2_pipeline.state_factory import create_initial_state
from rob2_pipeline.types import ChunkMeta, PacketSource, SourceDocument


def test_source_document_accepts_supplement_metadata():
    source: SourceDocument = {
        "document_id": "supplement:001",
        "document_name": "protocol.pdf",
        "document_role": "protocol",
        "source_kind": "rag_chunk",
        "path": "inputs/benchmark/supplement/TRIAL/protocol.pdf",
        "is_primary": False,
        "status": "parsed",
    }

    assert source["document_role"] == "protocol"
    assert source["is_primary"] is False


def test_chunk_meta_accepts_document_provenance():
    meta: ChunkMeta = {
        "text": "Allocation was concealed centrally.",
        "section": "Randomization",
        "page_numbers": [4],
        "score": 0.12,
        "document_id": "supplement:001",
        "document_name": "protocol.pdf",
        "document_role": "protocol",
        "source_kind": "rag_chunk",
        "source_path": "protocol.pdf",
    }

    assert meta["document_name"] == "protocol.pdf"


def test_packet_source_accepts_document_provenance():
    source: PacketSource = {
        "text": "Overall survival was the primary endpoint.",
        "section": "Endpoints",
        "page_numbers": [12],
        "score": 0.2,
        "matched_terms": ["endpoint"],
        "source_kind": "rag_chunk",
        "document_id": "supplement:001",
        "document_name": "protocol.pdf",
        "document_role": "protocol",
        "source_path": "protocol.pdf",
    }

    assert source["document_role"] == "protocol"


def test_initial_state_accepts_supplementary_paths():
    state = create_initial_state(
        "inputs/benchmark/TITAN.pdf",
        outcome="Overall Survival",
        supplementary_paths=["inputs/benchmark/supplement/TITAN/protocol.pdf"],
    )

    assert state["supplementary_paths"] == [
        "inputs/benchmark/supplement/TITAN/protocol.pdf"
    ]
    assert state["source_documents"] == []
    assert state["supplement_warnings"] == []
```

- [ ] **Step 2: Run type tests and verify failure**

Run:

```bash
uv run python -m pytest tests/test_types.py -q
```

Expected: FAIL because `SourceDocument` and supplement state fields are not defined.

- [ ] **Step 3: Add provenance types**

In `rob2_pipeline/types.py`, add `SourceDocument` after `ChunkMeta` and extend `ChunkMeta`, `PacketSource`, and `EvidenceFact`:

```python
class SourceDocument(TypedDict, total=False):
    document_id: str
    document_name: str
    document_role: str
    source_kind: str
    path: str
    is_primary: bool
    status: str
    error: str


class ChunkMeta(TypedDict, total=False):
    text: str
    section: str
    page_numbers: list[int]
    score: float
    document_id: str
    document_name: str
    document_role: str
    source_kind: str
    source_path: str
```

Update `PacketSource`:

```python
class PacketSource(TypedDict, total=False):
    text: str
    section: str
    page_numbers: list[int]
    score: float
    matched_terms: list[str]
    source_kind: str
    document_id: str
    document_name: str
    document_role: str
    source_path: str
```

Update `EvidenceFact`:

```python
class EvidenceFact(TypedDict, total=False):
    fact_type: str
    domain: str
    sq_ids: list[str]
    claim: str
    quote: str
    source_section: str
    page_numbers: list[int]
    confidence: float
    support_status: str
    missing_reason: str
    document_id: str
    document_name: str
    document_role: str
    source_kind: str
    source_path: str
```

- [ ] **Step 4: Add state fields**

In `rob2_pipeline/state.py`, import `SourceDocument` from `rob2_pipeline.types` and add fields to `RoB2State` near the input section:

```python
supplementary_paths: Annotated[list[str], take_latest]
source_documents: Annotated[list[SourceDocument], take_latest]
supplement_warnings: Annotated[list[str], take_latest]
```

- [ ] **Step 5: Initialize state**

In `rob2_pipeline/state_factory.py`, add these keys to the returned dict:

```python
"supplementary_paths": list(kwargs.get("supplementary_paths") or []),
"source_documents": [],
"supplement_warnings": [],
```

- [ ] **Step 6: Run type tests**

Run:

```bash
uv run python -m pytest tests/test_types.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add rob2_pipeline/types.py rob2_pipeline/state.py rob2_pipeline/state_factory.py tests/test_types.py
git commit -m "feat: add supplement source provenance state"
```

---

## Task 2: Add Supplement Classification And Metadata Helpers

**Files:**
- Create: `rob2_pipeline/ingestion/supplements.py`
- Test: `tests/test_supplements.py`

- [ ] **Step 1: Write failing classification tests**

Create `tests/test_supplements.py`:

```python
from pathlib import Path

from langchain_core.documents import Document

from rob2_pipeline.ingestion.supplements import (
    apply_source_metadata,
    build_source_document,
    classify_supplement,
)


def test_classify_supplement_from_filename():
    cases = {
        "nejmoa1903307_protocol.pdf": "protocol",
        "trial_statistical_analysis_plan.pdf": "sap",
        "nejmoa1903307_appendix.pdf": "appendix",
        "mmc1.pdf": "appendix",
        "nejmoa1903307_disclosures.pdf": "disclosure",
        "nejmoa1903307_data-sharing.pdf": "data_sharing",
        "ds_jco.19.00799.pdf": "data_sharing",
        "unlabeled-file.pdf": "unknown_supplement",
    }

    for filename, expected in cases.items():
        assert classify_supplement(Path(filename)) == expected


def test_build_source_document_uses_stable_supplement_id():
    source = build_source_document(
        Path("inputs/benchmark/supplement/TITAN/nejmoa1903307_protocol.pdf"),
        role="protocol",
        index=1,
    )

    assert source["document_id"] == "supplement:001"
    assert source["document_name"] == "nejmoa1903307_protocol.pdf"
    assert source["document_role"] == "protocol"
    assert source["source_kind"] == "rag_chunk"
    assert source["is_primary"] is False
    assert source["status"] == "pending"


def test_apply_source_metadata_preserves_existing_chunk_metadata():
    chunks = [
        Document(
            page_content="Protocol text.",
            metadata={"section": "Methods", "page_numbers": [3]},
        )
    ]
    source = build_source_document(Path("protocol.pdf"), role="protocol", index=1)

    result = apply_source_metadata(chunks, source)

    assert result[0].metadata["section"] == "Methods"
    assert result[0].metadata["page_numbers"] == [3]
    assert result[0].metadata["document_id"] == "supplement:001"
    assert result[0].metadata["document_name"] == "protocol.pdf"
    assert result[0].metadata["document_role"] == "protocol"
    assert result[0].metadata["source_kind"] == "rag_chunk"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run python -m pytest tests/test_supplements.py -q
```

Expected: FAIL because `rob2_pipeline.ingestion.supplements` does not exist.

- [ ] **Step 3: Create helper module**

Create `rob2_pipeline/ingestion/supplements.py`:

```python
from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document

from rob2_pipeline.types import SourceDocument


def classify_supplement(path: Path) -> str:
    name = path.name.casefold()
    compact = name.replace("_", "-")
    if "statistical-analysis" in compact or "analysis-plan" in compact or "sap" in compact:
        return "sap"
    if "protocol" in compact:
        return "protocol"
    if "data-sharing" in compact or compact.startswith("ds-") or compact.startswith("dss-"):
        return "data_sharing"
    if "disclosure" in compact or "coi" in compact or "conflict" in compact:
        return "disclosure"
    if "appendix" in compact or "supplement" in compact or compact.startswith("mmc"):
        return "appendix"
    return "unknown_supplement"


def build_source_document(path: Path, role: str, index: int) -> SourceDocument:
    return SourceDocument(
        document_id=f"supplement:{index:03d}",
        document_name=path.name,
        document_role=role,
        source_kind="rag_chunk",
        path=str(path),
        is_primary=False,
        status="pending",
    )


def primary_source_document(path: Path) -> SourceDocument:
    return SourceDocument(
        document_id="primary",
        document_name=path.name,
        document_role="primary",
        source_kind="rag_chunk",
        path=str(path),
        is_primary=True,
        status="parsed",
    )


def apply_source_metadata(
    chunks: list[Document], source: SourceDocument
) -> list[Document]:
    enriched: list[Document] = []
    for chunk in chunks:
        metadata = dict(chunk.metadata)
        metadata.update(
            {
                "document_id": source.get("document_id", ""),
                "document_name": source.get("document_name", ""),
                "document_role": source.get("document_role", ""),
                "source_kind": source.get("source_kind", "rag_chunk"),
                "source_path": source.get("path", ""),
            }
        )
        enriched.append(Document(page_content=chunk.page_content, metadata=metadata))
    return enriched
```

- [ ] **Step 4: Run supplement tests**

Run:

```bash
uv run python -m pytest tests/test_supplements.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rob2_pipeline/ingestion/supplements.py tests/test_supplements.py
git commit -m "feat: add supplement source helpers"
```

---

## Task 3: Let Docling Chunks Carry Source Metadata

**Files:**
- Modify: `rob2_pipeline/ingestion/docling_extract.py`
- Test: `tests/test_pdf_ingestion.py`

- [ ] **Step 1: Locate `_build_docling_chunks`**

Run:

```bash
rg "def _build_docling_chunks" rob2_pipeline tests
```

Expected: one production definition and existing tests or imports.

- [ ] **Step 2: Write failing metadata test**

Add to `tests/test_pdf_ingestion.py`:

```python
from langchain_core.documents import Document

from rob2_pipeline.ingestion.supplements import apply_source_metadata, primary_source_document


def test_primary_source_metadata_can_be_applied_to_docling_chunks(tmp_path):
    pdf_path = tmp_path / "ARCHES.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fake")
    chunks = [
        Document(
            page_content="Primary paper methods.",
            metadata={"section": "Methods", "page_numbers": [2]},
        )
    ]

    enriched = apply_source_metadata(chunks, primary_source_document(pdf_path))

    assert enriched[0].metadata["document_id"] == "primary"
    assert enriched[0].metadata["document_name"] == "ARCHES.pdf"
    assert enriched[0].metadata["document_role"] == "primary"
    assert enriched[0].metadata["source_kind"] == "rag_chunk"
```

- [ ] **Step 3: Run focused tests**

Run:

```bash
uv run python -m pytest tests/test_pdf_ingestion.py tests/test_supplements.py -q
```

Expected: PASS if Task 2 is complete. This establishes metadata application before wiring it into ingestion.

- [ ] **Step 4: Update `_build_docling_chunks` signature if useful**

If `_build_docling_chunks` currently only accepts `conv_result`, keep it unchanged and apply metadata outside it. If a small signature change is cleaner, change it to:

```python
def _build_docling_chunks(conv_result, source_metadata: dict | None = None) -> list[Document]:
    ...
    metadata = {
        "section": ...,
        "page_numbers": ...,
        "dl_meta": ...,
    }
    if source_metadata:
        metadata.update(source_metadata)
```

Preserve all existing tests that call `_build_docling_chunks(conv_result)`.

- [ ] **Step 5: Run ingestion tests**

Run:

```bash
uv run python -m pytest tests/test_pdf_ingestion.py tests/test_supplements.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add rob2_pipeline/ingestion/docling_extract.py tests/test_pdf_ingestion.py
git commit -m "feat: preserve source metadata on document chunks"
```

---

## Task 4: Wire Supplement Ingestion Into `pdf_ingest_node`

**Files:**
- Modify: `rob2_pipeline/ingestion/supplements.py`
- Modify: `rob2_pipeline/nodes/ingest.py`
- Test: `tests/test_supplements.py`

- [ ] **Step 1: Write failing helper test for supplement ingestion error handling**

Add to `tests/test_supplements.py`:

```python
from rob2_pipeline.ingestion.supplements import ingest_supplements


def test_ingest_supplements_records_missing_file_warning(tmp_path):
    missing = tmp_path / "missing_protocol.pdf"

    chunks, documents, warnings = ingest_supplements([str(missing)])

    assert chunks == []
    assert documents[0]["document_name"] == "missing_protocol.pdf"
    assert documents[0]["status"] == "missing"
    assert "Supplement not found" in warnings[0]
```

- [ ] **Step 2: Run helper test and verify failure**

Run:

```bash
uv run python -m pytest tests/test_supplements.py::test_ingest_supplements_records_missing_file_warning -q
```

Expected: FAIL because `ingest_supplements` is not defined.

- [ ] **Step 3: Implement `ingest_supplements`**

Add to `rob2_pipeline/ingestion/supplements.py`:

```python
def ingest_supplements(paths: list[str]) -> tuple[list[Document], list[SourceDocument], list[str]]:
    from rob2_pipeline.pdf_ingestion import (
        _build_docling_chunks,
        _configure_docling_runtime,
        _get_docling_converter,
    )

    chunks: list[Document] = []
    documents: list[SourceDocument] = []
    warnings: list[str] = []
    if not paths:
        return chunks, documents, warnings

    _configure_docling_runtime()
    converter = _get_docling_converter(use_ocr=False)
    for index, raw_path in enumerate(paths, start=1):
        path = Path(raw_path)
        role = classify_supplement(path)
        source = build_source_document(path, role, index)
        if not path.exists():
            source["status"] = "missing"
            source["error"] = f"Supplement not found: {path}"
            documents.append(source)
            warnings.append(source["error"])
            continue
        try:
            conv_result = converter.convert(str(path))
            source["status"] = "parsed"
            source_chunks = apply_source_metadata(_build_docling_chunks(conv_result), source)
            chunks.extend(source_chunks)
        except Exception as error:  # noqa: BLE001
            source["status"] = "failed"
            source["error"] = f"Supplement parse failed: {path}: {error}"
            warnings.append(source["error"])
        documents.append(source)
    return chunks, documents, warnings
```

- [ ] **Step 4: Run supplement tests**

Run:

```bash
uv run python -m pytest tests/test_supplements.py -q
```

Expected: PASS.

- [ ] **Step 5: Wire primary and supplement source metadata in `pdf_ingest_node`**

In `rob2_pipeline/nodes/ingest.py`, import:

```python
from pathlib import Path
from rob2_pipeline.ingestion.supplements import (
    apply_source_metadata,
    ingest_supplements,
    primary_source_document,
)
```

After primary `docling_chunks = _build_docling_chunks(conv_result)`, add:

```python
primary_source = primary_source_document(Path(pdf_path))
docling_chunks = apply_source_metadata(docling_chunks, primary_source)
supplement_chunks, supplement_documents, supplement_warnings = ingest_supplements(
    list(state.get("supplementary_paths") or [])
)
docling_chunks = [*docling_chunks, *supplement_chunks]
source_documents = [primary_source, *supplement_documents]
```

Include these in every successful primary-Docling return:

```python
"docling_chunks": docling_chunks,
"source_documents": source_documents,
"supplement_warnings": supplement_warnings,
```

In the fallback return where `docling_chunks` is `[]`, include:

```python
"source_documents": [primary_source_document(Path(pdf_path))],
"supplement_warnings": [],
```

- [ ] **Step 6: Add node-level test with monkeypatching**

Add to `tests/test_supplements.py`:

```python
def test_pdf_ingest_node_appends_supplement_chunks(monkeypatch):
    import rob2_pipeline.nodes.ingest as node
    from langchain_core.documents import Document

    evidence = node.paper_evidence_from_sections({"methods": "Randomized."})

    monkeypatch.setattr(node, "extract_full_text", lambda path: "Primary text")
    monkeypatch.setattr(node, "_configure_docling_runtime", lambda: None)
    monkeypatch.setattr(node, "_get_docling_converter", lambda use_ocr=False: object())
    monkeypatch.setattr(
        node,
        "_build_docling_chunks",
        lambda conv_result: [
            Document(page_content="Primary chunk", metadata={"section": "Methods", "page_numbers": [1]})
        ],
    )
    monkeypatch.setattr(node, "build_document_repr", lambda doc: type("DocRepr", (), {"full_text": "Primary text", "to_prompt_repr": lambda self: "Primary text", "blocks": []})())
    monkeypatch.setattr(node, "extract_structural_paper_evidence", lambda doc_repr: evidence)
    monkeypatch.setattr(node, "allow_remote_evidence_extraction", lambda: False)
    monkeypatch.setattr(
        node,
        "ingest_supplements",
        lambda paths: (
            [Document(page_content="Protocol chunk", metadata={"section": "Protocol", "page_numbers": [2], "document_id": "supplement:001", "document_name": "protocol.pdf", "document_role": "protocol", "source_kind": "rag_chunk", "source_path": "protocol.pdf"})],
            [{"document_id": "supplement:001", "document_name": "protocol.pdf", "document_role": "protocol", "source_kind": "rag_chunk", "path": "protocol.pdf", "is_primary": False, "status": "parsed"}],
            [],
        ),
    )

    class Result:
        document = object()

    class Converter:
        def convert(self, path):
            return Result()

    monkeypatch.setattr(node, "_get_docling_converter", lambda use_ocr=False: Converter())

    result = node.pdf_ingest_node(
        {"pdf_path": "primary.pdf", "supplementary_paths": ["protocol.pdf"]}
    )

    assert len(result["docling_chunks"]) == 2
    assert result["docling_chunks"][0].metadata["document_id"] == "primary"
    assert result["docling_chunks"][1].metadata["document_id"] == "supplement:001"
    assert result["source_documents"][0]["document_role"] == "primary"
    assert result["source_documents"][1]["document_role"] == "protocol"
```

- [ ] **Step 7: Run supplement tests**

Run:

```bash
uv run python -m pytest tests/test_supplements.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add rob2_pipeline/ingestion/supplements.py rob2_pipeline/nodes/ingest.py tests/test_supplements.py
git commit -m "feat: ingest supplementary PDFs into RAG chunks"
```

---

## Task 5: Preserve Provenance Through RAG

**Files:**
- Modify: `rob2_pipeline/rag.py`
- Modify: `rob2_pipeline/nodes/rag_retrieval.py`
- Test: `tests/test_rag.py`
- Test: `tests/test_rag_retrieval_node.py`

- [ ] **Step 1: Write failing `_doc_key` test**

Add to `tests/test_rag.py`:

```python
from langchain_core.documents import Document

from rob2_pipeline.rag import _doc_key


def test_doc_key_includes_document_id():
    left = Document(
        page_content="Same text",
        metadata={"section": "Methods", "page_numbers": [1], "document_id": "primary"},
    )
    right = Document(
        page_content="Same text",
        metadata={"section": "Methods", "page_numbers": [1], "document_id": "supplement:001"},
    )

    assert _doc_key(left) != _doc_key(right)
```

- [ ] **Step 2: Write failing retrieval metadata test**

Add to `tests/test_rag_retrieval_node.py`:

```python
def test_rag_retrieval_node_preserves_document_metadata(monkeypatch):
    import rob2_pipeline.nodes.rag_retrieval as node

    chunks = [
        _make_doc("Protocol says OS was primary.", section="Protocol")
    ]
    chunks[0].metadata.update(
        {
            "document_id": "supplement:001",
            "document_name": "protocol.pdf",
            "document_role": "protocol",
            "source_kind": "rag_chunk",
            "source_path": "protocol.pdf",
        }
    )
    monkeypatch.setattr(node, "build_index", lambda _: object())
    monkeypatch.setattr(node, "build_filtered_index", lambda chunks, keywords: None)
    monkeypatch.setattr(
        node,
        "retrieve_adaptive",
        lambda index, filtered, queries: (
            "Protocol says OS was primary.",
            [
                {
                    "text": "Protocol says OS was primary.",
                    "section": "Protocol",
                    "page_numbers": [5],
                    "score": 0.1,
                    "document_id": "supplement:001",
                    "document_name": "protocol.pdf",
                    "document_role": "protocol",
                    "source_kind": "rag_chunk",
                    "source_path": "protocol.pdf",
                }
            ],
        ),
    )

    result = node.rag_retrieval_node(_base_state(chunks))

    source = result["rag_chunk_metadata"]["d5"][0]
    assert source["document_name"] == "protocol.pdf"
    assert source["document_role"] == "protocol"
```

- [ ] **Step 3: Run focused tests and verify failure**

Run:

```bash
uv run python -m pytest tests/test_rag.py::test_doc_key_includes_document_id tests/test_rag_retrieval_node.py::test_rag_retrieval_node_preserves_document_metadata -q
```

Expected: `_doc_key` test fails until provenance is included.

- [ ] **Step 4: Update `_doc_key`**

In `rob2_pipeline/rag.py`, update `_doc_key`:

```python
def _doc_key(doc: Document) -> str:
    pages = ",".join(str(page) for page in doc.metadata.get("page_numbers") or [])
    section = doc.metadata.get("section", "")
    document_id = doc.metadata.get("document_id", "")
    return f"{document_id}|{section}|{pages}|{doc.page_content[:160]}"
```

- [ ] **Step 5: Copy provenance into `retrieve_adaptive` metas**

In `retrieve_adaptive()`, when appending `ChunkMeta`, include:

```python
metas.append(
    ChunkMeta(
        text=page_content,
        section=doc.metadata.get("section", ""),
        page_numbers=list(doc.metadata.get("page_numbers") or []),
        score=scores[key],
        document_id=doc.metadata.get("document_id", ""),
        document_name=doc.metadata.get("document_name", ""),
        document_role=doc.metadata.get("document_role", ""),
        source_kind=doc.metadata.get("source_kind", "rag_chunk"),
        source_path=doc.metadata.get("source_path", ""),
    )
)
```

- [ ] **Step 6: Run RAG tests**

Run:

```bash
uv run python -m pytest tests/test_rag.py tests/test_rag_retrieval_node.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add rob2_pipeline/rag.py rob2_pipeline/nodes/rag_retrieval.py tests/test_rag.py tests/test_rag_retrieval_node.py
git commit -m "feat: preserve document provenance in retrieval"
```

---

## Task 6: Add CT.gov Candidate Sources And Source Ranking

**Files:**
- Modify: `rob2_pipeline/nodes/evidence_source_selection.py`
- Modify: `rob2_pipeline/nodes/evidence_packet_grading.py`
- Test: `tests/test_evidence_packets.py`

- [ ] **Step 1: Write failing CT.gov candidate test**

Add to `tests/test_evidence_packets.py`:

```python
def test_d5_packet_includes_ctgov_source_without_page_numbers():
    evidence = empty_paper_evidence("test")
    state = {
        "outcome": "Overall Survival",
        "evidence": evidence,
        "ctgov_outcomes": "Primary Outcome: Overall Survival. Time Frame: from randomization to death.",
        "registered_endpoint": "Overall Survival",
        "registered_secondary_endpoints": "Progression-Free Survival",
        "registered_analysis": "Cox proportional hazards model",
        "rag_chunk_metadata": {"d1": [], "d2": [], "d3": [], "d4": [], "d5": []},
        "retrieval_grades": {},
    }

    result = build_evidence_packets(state)

    sources = result["evidence_packets"]["5.1"]["sources"]
    assert any(source.get("source_kind") == "ctgov" for source in sources)
    ctgov = [source for source in sources if source.get("source_kind") == "ctgov"][0]
    assert ctgov["document_name"] == "ClinicalTrials.gov"
    assert ctgov["document_role"] == "registry"
    assert ctgov["page_numbers"] == []
```

- [ ] **Step 2: Write failing role-priority test**

Add to `tests/test_evidence_packets.py`:

```python
def test_d5_packet_prefers_protocol_over_primary_result_when_terms_match():
    state = _state_with_chunks(
        "d5",
        [
            {
                "text": "Published results report progression-free survival HR 0.70.",
                "section": "Results",
                "page_numbers": [8],
                "score": 0.1,
                "document_id": "primary",
                "document_name": "paper.pdf",
                "document_role": "primary",
                "source_kind": "rag_chunk",
                "source_path": "paper.pdf",
            },
            {
                "text": "The protocol prespecified progression-free survival as a secondary endpoint.",
                "section": "Endpoints",
                "page_numbers": [12],
                "score": 0.2,
                "document_id": "supplement:001",
                "document_name": "protocol.pdf",
                "document_role": "protocol",
                "source_kind": "rag_chunk",
                "source_path": "protocol.pdf",
            },
        ],
        outcome="Progression-Free Survival",
    )

    result = build_evidence_packets(state)

    first = result["evidence_packets"]["5.2"]["sources"][0]
    assert first["document_role"] == "protocol"
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
uv run python -m pytest tests/test_evidence_packets.py::test_d5_packet_includes_ctgov_source_without_page_numbers tests/test_evidence_packets.py::test_d5_packet_prefers_protocol_over_primary_result_when_terms_match -q
```

Expected: FAIL because CT.gov sources and role ranking are not implemented.

- [ ] **Step 4: Add source role preferences and CT.gov sources**

In `rob2_pipeline/nodes/evidence_source_selection.py`, add:

```python
DOMAIN_SOURCE_ROLE_PREFERENCES = {
    "d1": ["primary", "protocol", "appendix"],
    "d2": ["primary", "protocol", "sap", "appendix"],
    "d3": ["primary", "appendix", "sap"],
    "d4": ["primary", "protocol", "sap", "appendix"],
    "d5": ["protocol", "sap", "registry", "primary", "appendix"],
}


def role_rank(domain: str, role: str) -> int:
    preferences = DOMAIN_SOURCE_ROLE_PREFERENCES.get(domain, [])
    try:
        return preferences.index(role)
    except ValueError:
        return len(preferences) + 1
```

Add:

```python
def ctgov_sources(state: RoB2State, contract: EvidenceContract) -> list[dict]:
    fields_by_domain = {
        "d1": ["ctgov_design"],
        "d2": ["ctgov_design"],
        "d3": ["ctgov_flow"],
        "d5": [
            "ctgov_outcomes",
            "registered_endpoint",
            "registered_secondary_endpoints",
            "registered_analysis",
        ],
    }
    fields = fields_by_domain.get(contract.domain, [])
    text_parts = [str(state.get(field, "")).strip() for field in fields]
    text = "\n\n".join(part for part in text_parts if part and part != "Not reported")
    if not text:
        return []
    return [
        {
            "text": text,
            "section": "ClinicalTrials.gov",
            "page_numbers": [],
            "score": 0.5,
            "source_kind": "ctgov",
            "document_id": "ctgov",
            "document_name": "ClinicalTrials.gov",
            "document_role": "registry",
            "source_path": "",
        }
    ]
```

In `candidate_sources()`, extend raw sources:

```python
raw_sources.extend(ctgov_sources(state, contract))
raw_sources.extend(fallback_sources(state, contract))
```

When building `PacketSource`, copy provenance fields from `raw`.

- [ ] **Step 5: Rank packet candidates by matched terms, source role, and score**

In `rob2_pipeline/nodes/evidence_packets.py`, change the `ranked = sorted(...)` key to:

```python
from rob2_pipeline.nodes.evidence_source_selection import role_rank

ranked = sorted(
    candidates,
    key=lambda source: (
        -len(source.get("matched_terms", [])),
        role_rank(contract.domain, source.get("document_role", "")),
        source.get("score", 1e9),
    ),
)
```

- [ ] **Step 6: Preserve provenance in `source_to_fact`**

In `rob2_pipeline/nodes/evidence_packet_grading.py`, update `source_to_fact()` to include:

```python
document_id=source.get("document_id", ""),
document_name=source.get("document_name", ""),
document_role=source.get("document_role", ""),
source_kind=source.get("source_kind", ""),
source_path=source.get("source_path", ""),
```

If `EvidenceFact(...)` is built with a dict literal, add the same keys.

- [ ] **Step 7: Run evidence packet tests**

Run:

```bash
uv run python -m pytest tests/test_evidence_packets.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add rob2_pipeline/nodes/evidence_source_selection.py rob2_pipeline/nodes/evidence_packet_grading.py rob2_pipeline/nodes/evidence_packets.py tests/test_evidence_packets.py
git commit -m "feat: rank evidence packets by source provenance"
```

---

## Task 7: Render Provenance In Packet Blocks

**Files:**
- Modify: `rob2_pipeline/nodes/evidence_packets.py`
- Test: `tests/test_evidence_packets.py`

- [ ] **Step 1: Write failing packet rendering test**

Add to `tests/test_evidence_packets.py`:

```python
def test_packet_block_renders_document_name_and_role():
    state = _state_with_chunks(
        "d5",
        [
            {
                "text": "The protocol prespecified overall survival as the primary endpoint.",
                "section": "Endpoints",
                "page_numbers": [12],
                "score": 0.1,
                "document_id": "supplement:001",
                "document_name": "protocol.pdf",
                "document_role": "protocol",
                "source_kind": "rag_chunk",
                "source_path": "protocol.pdf",
            }
        ],
        outcome="Overall Survival",
    )
    result = build_evidence_packets(state)

    block = packet_block_for_domain(result["evidence_packets"], "d5")

    assert "protocol.pdf" in block
    assert "protocol" in block
    assert "page 12" in block
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run python -m pytest tests/test_evidence_packets.py::test_packet_block_renders_document_name_and_role -q
```

Expected: FAIL if renderer still emits only page and section.

- [ ] **Step 3: Update packet source line rendering**

In `packet_block_for_domain()`, replace source line construction with:

```python
document_name = source.get("document_name") or "Unknown document"
document_role = source.get("document_role") or source.get("source_kind") or "source"
pages = source.get("page_numbers") or []
page = f"page {pages[0]}" if pages else "no page"
section = source.get("section") or "Unknown section"
text = compact(source.get("text", ""), 700)
source_lines.append(f"- {document_role} ({document_name}), {page}, {section}: {text}")
```

- [ ] **Step 4: Run packet tests**

Run:

```bash
uv run python -m pytest tests/test_evidence_packets.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add rob2_pipeline/nodes/evidence_packets.py tests/test_evidence_packets.py
git commit -m "feat: render evidence packet source provenance"
```

---

## Task 8: Update Verification Missing-Page Rules

**Files:**
- Modify: `rob2_pipeline/nodes/verification.py` or `rob2_pipeline/nodes/evidence_packet_grading.py`
- Test: `tests/test_verification.py`
- Test: `tests/test_evidence_packets.py`

- [ ] **Step 1: Locate missing-page logic**

Run:

```bash
rg "missing_page_source|page_numbers|source_kind" rob2_pipeline/nodes tests/test_verification.py tests/test_evidence_packets.py
```

Expected: identify the function that adds `missing_page_source`.

- [ ] **Step 2: Write failing CT.gov exemption test**

Add to the file that currently tests missing-page behavior, likely `tests/test_evidence_packets.py` or `tests/test_verification.py`:

```python
def test_ctgov_source_is_not_flagged_missing_page_source():
    evidence = empty_paper_evidence("test")
    state = {
        "outcome": "Overall Survival",
        "evidence": evidence,
        "ctgov_outcomes": "Primary Outcome: Overall Survival.",
        "registered_endpoint": "Overall Survival",
        "registered_secondary_endpoints": "",
        "registered_analysis": "",
        "rag_chunk_metadata": {"d1": [], "d2": [], "d3": [], "d4": [], "d5": []},
        "retrieval_grades": {},
    }

    result = build_evidence_packets(state)

    assert "missing_page_source" not in result["evidence_packets"]["5.1"]["negative_flags"]
```

- [ ] **Step 3: Run test and verify failure if rule is too strict**

Run:

```bash
uv run python -m pytest tests/test_evidence_packets.py::test_ctgov_source_is_not_flagged_missing_page_source -q
```

Expected: FAIL until `ctgov` is exempt, or PASS if existing logic only flags `rag_chunk`.

- [ ] **Step 4: Update missing-page rule**

Where `missing_page_source` is added, ensure only real RAG chunks require pages:

```python
page_required_kinds = {"rag_chunk"}
if source.get("source_kind", "rag_chunk") in page_required_kinds and not source.get("page_numbers"):
    flags.append("missing_page_source")
```

Keep existing tests that assert real `rag_chunk` without pages is still flagged.

- [ ] **Step 5: Run verification and packet tests**

Run:

```bash
uv run python -m pytest tests/test_evidence_packets.py tests/test_verification.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add rob2_pipeline/nodes/verification.py rob2_pipeline/nodes/evidence_packet_grading.py tests/test_verification.py tests/test_evidence_packets.py
git commit -m "fix: exempt structured sources from page metadata warnings"
```

---

## Task 9: Add Pipeline API And JSON Output Fields

**Files:**
- Modify: `rob2_pipeline/pipeline.py`
- Test: `tests/test_pipeline.py` or existing pipeline test file

- [ ] **Step 1: Write failing pipeline API test**

If `tests/test_pipeline.py` does not exist, create it:

```python
from pathlib import Path

from rob2_pipeline.pipeline import _assessment_json, run_assessment


def test_assessment_json_includes_supplement_fields():
    state = {
        "pdf_path": "paper.pdf",
        "supplementary_paths": ["protocol.pdf"],
        "source_documents": [
            {
                "document_id": "supplement:001",
                "document_name": "protocol.pdf",
                "document_role": "protocol",
                "status": "parsed",
            }
        ],
        "supplement_warnings": [],
        "rag_chunk_metadata": {},
    }

    data = _assessment_json(state)

    assert data["supplementary_paths"] == ["protocol.pdf"]
    assert data["source_documents"][0]["document_name"] == "protocol.pdf"
    assert data["supplement_warnings"] == []
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run python -m pytest tests/test_pipeline.py -q
```

Expected: FAIL until `JSON_OUTPUT_KEYS` includes supplement fields.

- [ ] **Step 3: Extend JSON output keys**

In `rob2_pipeline/pipeline.py`, add to `JSON_OUTPUT_KEYS`:

```python
"supplementary_paths",
"source_documents",
"supplement_warnings",
```

- [ ] **Step 4: Extend `run_assessment` signature**

Change signature:

```python
def run_assessment(
    pdf_path: str,
    outcome: str | None = None,
    effect_of_interest: str = DEFAULT_EFFECT_OF_INTEREST,
    output_dir: str = "outputs/",
    supplementary_paths: list[str] | None = None,
) -> RoB2State:
```

Change graph invocation:

```python
state = graph.invoke(
    create_initial_state(
        pdf_path,
        outcome,
        effect_of_interest,
        supplementary_paths=supplementary_paths or [],
    )
)
```

- [ ] **Step 5: Run pipeline test**

Run:

```bash
uv run python -m pytest tests/test_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 6: Run state and pipeline-related tests**

Run:

```bash
uv run python -m pytest tests/test_types.py tests/test_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add rob2_pipeline/pipeline.py tests/test_pipeline.py
git commit -m "feat: expose supplement metadata in assessment output"
```

---

## Task 10: Add Main CLI Supplement Flags

**Files:**
- Modify: `main.py`
- Modify: `rob2_pipeline/io.py`
- Test: `tests/test_io.py`

- [ ] **Step 1: Write failing supplement discovery helper test**

Add to `tests/test_io.py`:

```python
from rob2_pipeline.io import discover_supplements_for_pdf


def test_discover_supplements_for_pdf_uses_pdf_stem(tmp_path):
    supplement_root = tmp_path / "supplements"
    trial_dir = supplement_root / "TITAN"
    trial_dir.mkdir(parents=True)
    protocol = trial_dir / "protocol.pdf"
    appendix = trial_dir / "appendix.pdf"
    protocol.write_bytes(b"pdf")
    appendix.write_bytes(b"pdf")

    result = discover_supplements_for_pdf(tmp_path / "TITAN.pdf", supplement_root)

    assert result == [appendix, protocol]
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run python -m pytest tests/test_io.py::test_discover_supplements_for_pdf_uses_pdf_stem -q
```

Expected: FAIL because helper does not exist.

- [ ] **Step 3: Add discovery helper**

In `rob2_pipeline/io.py`, add:

```python
def discover_supplements_for_pdf(pdf_path: Path, supplement_root: Path | None) -> list[Path]:
    if supplement_root is None:
        return []
    trial_dir = supplement_root / pdf_path.stem
    if not trial_dir.exists() or not trial_dir.is_dir():
        return []
    return sorted(path for path in trial_dir.glob("*.pdf") if path.is_file())
```

- [ ] **Step 4: Wire CLI flags**

In `main.py`, import `Path` if needed and import `discover_supplements_for_pdf`:

```python
from pathlib import Path
from rob2_pipeline.io import default_output_dir, discover_pdf_inputs, discover_supplements_for_pdf
```

Add parser args:

```python
parser.add_argument(
    "--supplement",
    action="append",
    default=[],
    help="Supplement PDF path. Can be passed multiple times.",
)
parser.add_argument(
    "--supplement-dir",
    default=None,
    help="Directory containing per-trial supplement folders named by primary PDF stem.",
)
```

Before `run_assessment`, compute:

```python
supplement_paths = list(args.supplement or [])
supplement_paths.extend(
    str(path)
    for path in discover_supplements_for_pdf(
        pdf_path, Path(args.supplement_dir) if args.supplement_dir else None
    )
)
```

Pass:

```python
supplementary_paths=supplement_paths,
```

- [ ] **Step 5: Run IO tests**

Run:

```bash
uv run python -m pytest tests/test_io.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add main.py rob2_pipeline/io.py tests/test_io.py
git commit -m "feat: add CLI supplement inputs"
```

---

## Task 11: Add Benchmark Supplement Discovery

**Files:**
- Modify: `rob2_pipeline/benchmark.py`
- Modify: `benchmark.py`
- Test: `tests/test_benchmark.py`

- [ ] **Step 1: Write failing benchmark supplement discovery tests**

Add to `tests/test_benchmark.py`:

```python
from rob2_pipeline.benchmark import find_supplements_for_trial


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
```

- [ ] **Step 2: Write failing run_benchmark pass-through test**

Add to `tests/test_benchmark.py`:

```python
def test_run_benchmark_passes_discovered_supplements(tmp_path, monkeypatch):
    from rob2_pipeline.benchmark import run_benchmark

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

    run_benchmark(
        pdf_dir=pdf_dir,
        reference_csvs={"OS": reference_csv},
        outcome_map=[{"trial": "TITAN", "outcome_code": "OS", "cohort": "unspecified"}],
        output_dir=output_dir,
        supplement_dir=supplement_root,
        use_supplements=True,
    )

    assert calls[0]["supplementary_paths"] == [str(protocol)]
```

- [ ] **Step 3: Run benchmark tests and verify failure**

Run:

```bash
uv run python -m pytest tests/test_benchmark.py::test_find_supplements_for_trial_handles_spaces_and_case tests/test_benchmark.py::test_run_benchmark_passes_discovered_supplements -q
```

Expected: FAIL because helper/API are not implemented.

- [ ] **Step 4: Add supplement discovery helper**

In `rob2_pipeline/benchmark.py`, add:

```python
def find_supplements_for_trial(supplement_dir: Path, trial_name: str) -> list[Path]:
    if not supplement_dir.exists() or not supplement_dir.is_dir():
        return []
    target = trial_name.strip().casefold()
    for candidate in supplement_dir.iterdir():
        if candidate.is_dir() and candidate.name.strip().casefold() == target:
            return sorted(path for path in candidate.glob("*.pdf") if path.is_file())
    return []
```

- [ ] **Step 5: Extend `run_benchmark` signature and call**

Change signature:

```python
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
```

Inside the trial loop, after `pdf_path` resolution:

```python
supplement_paths: list[Path] = []
if use_supplements and supplement_policy != "none" and supplement_dir is not None:
    supplement_paths = find_supplements_for_trial(Path(supplement_dir), trial_name)
trial_result["supplementary_paths"] = [str(path) for path in supplement_paths]
trial_result["supplements_found"] = len(supplement_paths)
trial_result["supplement_policy"] = supplement_policy
if use_supplements and supplement_policy == "required" and not supplement_paths:
    trial_result["skipped"] = True
    trial_result["notes"] = f"Required supplements not found in {supplement_dir}"
    results.append(trial_result)
    continue
```

Pass into `run_assessment`:

```python
supplementary_paths=[str(path) for path in supplement_paths],
```

- [ ] **Step 6: Add benchmark CLI flags**

In top-level `benchmark.py`, add args:

```python
parser.add_argument(
    "--use-supplements",
    action="store_true",
    help="Use discovered supplements for each benchmark trial.",
)
parser.add_argument(
    "--supplement-dir",
    default=None,
    help="Directory containing per-trial supplement folders.",
)
parser.add_argument(
    "--supplement-policy",
    choices=["auto", "required", "none"],
    default="auto",
    help="How benchmark should treat missing supplements.",
)
```

In dry-run output, compute supplements with `find_supplements_for_trial()` and print:

```python
if args.use_supplements and args.supplement_dir:
    supplements = find_supplements_for_trial(Path(args.supplement_dir), trial)
    supplement_names = ", ".join(path.name for path in supplements) or "none"
    print(f"  supplements: {supplement_names}")
```

Pass args into `run_benchmark()`:

```python
supplement_dir=Path(args.supplement_dir) if args.supplement_dir else None,
use_supplements=args.use_supplements,
supplement_policy=args.supplement_policy,
```

- [ ] **Step 7: Run benchmark tests**

Run:

```bash
uv run python -m pytest tests/test_benchmark.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add rob2_pipeline/benchmark.py benchmark.py tests/test_benchmark.py
git commit -m "feat: add benchmark supplement discovery"
```

---

## Task 12: Final Verification And Documentation Update

**Files:**
- Modify: `README.md`
- Modify: `ARCHITECTURE.md`

- [ ] **Step 1: Update README CLI examples**

Add a short supplement example:

Run with explicit supplements:

```bash
uv run python main.py inputs/benchmark/TITAN.pdf \
  --outcome "Overall Survival" \
  --supplement inputs/benchmark/supplement/TITAN/nejmoa1903307_protocol.pdf
```

Run benchmark with discovered supplements:

```bash
uv run python benchmark.py \
  --outcome-map TITAN:OS \
  --use-supplements \
  --supplement-dir inputs/benchmark/supplement
```

- [ ] **Step 2: Update architecture state model**

In `ARCHITECTURE.md`, add bullets for:

- `supplementary_paths`
- `source_documents`
- `supplement_warnings`
- provenance fields in `rag_sources`
- CT.gov packet source behavior

- [ ] **Step 3: Run focused test suite**

Run:

```bash
uv run python -m pytest tests/test_types.py tests/test_supplements.py tests/test_pdf_ingestion.py tests/test_rag.py tests/test_rag_retrieval_node.py tests/test_evidence_packets.py tests/test_verification.py tests/test_io.py tests/test_benchmark.py tests/test_pipeline.py -q
```

Expected: PASS. If `tests/test_pipeline.py` was not created because an equivalent existing pipeline test file was used, replace it in the command with that file.

- [ ] **Step 4: Run full test suite**

Run:

```bash
uv run python -m pytest -q
```

Expected: PASS.

- [ ] **Step 5: Run dry-run benchmark supplement check**

Run:

```bash
uv run python benchmark.py \
  --outcome-map TITAN:OS "SWOG 1216:OS" \
  --dry-run \
  --use-supplements \
  --supplement-dir inputs/benchmark/supplement
```

Expected output includes supplement names for `TITAN` and `SWOG 1216`.

- [ ] **Step 6: Commit**

```bash
git add README.md ARCHITECTURE.md
git commit -m "docs: document supplement-enriched pipeline"
```

---

## Self-Review

- Spec coverage: tasks cover state/API plumbing, supplement ingestion, provenance preservation, RAG metadata, packet source ranking, CT.gov structured sources, benchmark discovery, CLI flags, output JSON, tests, and docs.
- Scope control: manifest-based benchmark folders, LLM supplement classification, and targeted fact extraction are intentionally deferred.
- Type consistency: the plan consistently uses `supplementary_paths`, `source_documents`, `supplement_warnings`, `document_id`, `document_name`, `document_role`, `source_kind`, and `source_path`.
- Compatibility: default behavior remains primary-only unless `supplementary_paths` or `use_supplements=True` is provided.
