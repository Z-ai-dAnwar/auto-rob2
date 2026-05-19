import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from rob2_pipeline.cache import read_cache, write_cache
from rob2_pipeline.nodes.common import call_node_llm
from rob2_pipeline.providers.base import LLMResponse


class _FakeProvider:
    def __init__(self, content: str):
        self._content = content

    def complete(self, system: str, user: str) -> LLMResponse:
        return LLMResponse(self._content, "test-model", 1, 1, 1.0)


def test_cache_miss_and_write(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ROB2_USE_CACHE", "1")
    prompt = "Prompt text"
    node = "node1"
    assert read_cache(node, prompt) is None

    with patch(
        "rob2_pipeline.nodes.common.build_provider",
        return_value=_FakeProvider("response"),
    ):
        response, _, _ = call_node_llm({}, prompt, node)

    assert response == "response"
    assert read_cache(node, prompt) == "response"


def test_call_node_llm_logs_chunk_sources(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ROB2_USE_CACHE", "1")

    with patch(
        "rob2_pipeline.nodes.common.build_provider",
        return_value=_FakeProvider("response"),
    ):
        _, log, _ = call_node_llm(
            {}, "Prompt text", "node_with_sources", chunk_sources=["[page 1, Methods]"]
        )

    assert log[0]["chunk_sources"] == ["[page 1, Methods]"]


def test_cache_hit_uses_stored_response(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ROB2_USE_CACHE", "1")
    prompt = "Another prompt"
    node = "node2"
    write_cache(node, prompt, "cached")
    with patch(
        "rob2_pipeline.nodes.common.build_provider",
        return_value=_FakeProvider("response"),
    ):
        response, _, _ = call_node_llm({}, prompt, node)

    assert response == "cached"


def test_cache_expired_entry_is_miss(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ROB2_USE_CACHE", "1")
    monkeypatch.setenv("ROB2_CACHE_TTL_DAYS", "0")
    prompt = "Expire me"
    node = "node3"
    write_cache(node, prompt, "stale")
    cache_file = next(Path(".rob2_cache").glob("*.json"))
    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    payload["cached_at_iso"] = (
        datetime.now(timezone.utc) - timedelta(days=10)
    ).isoformat()
    cache_file.write_text(json.dumps(payload), encoding="utf-8")
    with patch(
        "rob2_pipeline.nodes.common.build_provider", return_value=_FakeProvider("fresh")
    ):
        response, _, _ = call_node_llm({}, prompt, node)

    assert response == "fresh"


def test_cache_disabled_returns_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ROB2_USE_CACHE", raising=False)
    prompt = "No cache"
    node = "node4"
    write_cache(node, prompt, "ignored")
    with patch(
        "rob2_pipeline.nodes.common.build_provider", return_value=_FakeProvider("live")
    ):
        response, _, _ = call_node_llm({}, prompt, node)

    assert response == "live"
    assert read_cache(node, prompt) is None
