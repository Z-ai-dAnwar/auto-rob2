from rob2_pipeline.types import ChunkMeta, LLMCallLogEntry


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
