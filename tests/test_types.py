from rob2_pipeline.state_factory import create_initial_state
from rob2_pipeline.types import ChunkMeta, LLMCallLogEntry, PacketSource, SourceDocument


def test_chunk_meta_fields():
    meta: ChunkMeta = {
        "text": "hello",
        "section": "Methods",
        "page_numbers": [3],
        "score": 0.9,
    }

    assert meta["section"] == "Methods"


def test_llm_call_log_entry_accepts_chunk_sources():
    entry: LLMCallLogEntry = {
        "node": "domain1_sq",
        "prompt_length_chars": 100,
        "response_length_chars": 50,
        "latency_ms": 10,
        "cache_hit": False,
        "chunk_sources": ["[page 3, Methods]"],
    }

    assert entry["chunk_sources"] == ["[page 3, Methods]"]


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
