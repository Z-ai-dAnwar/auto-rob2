import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from rob2_pipeline.cache import read_cache, write_cache
from rob2_pipeline.nodes.common import call_node_llm


def test_cache_miss_and_write(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ROB2_USE_CACHE", "1")
    prompt = "Prompt text"
    node = "node1"
    assert read_cache(node, prompt) is None

    with patch("rob2_pipeline.llm_client.get_llm", return_value=object()), patch(
        "rob2_pipeline.llm_client.call_llm", return_value="response"
    ) as call_mock:
        response, _, _ = call_node_llm({}, prompt, node)

    assert response == "response"
    assert call_mock.call_count == 1
    assert read_cache(node, prompt) == "response"


def test_cache_hit_uses_stored_response(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ROB2_USE_CACHE", "1")
    prompt = "Another prompt"
    node = "node2"
    write_cache(node, prompt, "cached")
    with patch("rob2_pipeline.llm_client.get_llm", return_value=object()), patch(
        "rob2_pipeline.llm_client.call_llm", return_value="response"
    ) as call_mock:
        response, _, _ = call_node_llm({}, prompt, node)

    assert response == "cached"
    assert call_mock.call_count == 0


def test_cache_expired_entry_is_miss(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ROB2_USE_CACHE", "1")
    monkeypatch.setenv("ROB2_CACHE_TTL_DAYS", "0")
    prompt = "Expire me"
    node = "node3"
    write_cache(node, prompt, "stale")
    cache_file = next(Path(".rob2_cache").glob("*.json"))
    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    payload["cached_at_iso"] = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    cache_file.write_text(json.dumps(payload), encoding="utf-8")
    with patch("rob2_pipeline.llm_client.get_llm", return_value=object()), patch(
        "rob2_pipeline.llm_client.call_llm", return_value="fresh"
    ) as call_mock:
        response, _, _ = call_node_llm({}, prompt, node)

    assert response == "fresh"
    assert call_mock.call_count == 1


def test_cache_disabled_returns_none(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ROB2_USE_CACHE", raising=False)
    prompt = "No cache"
    node = "node4"
    write_cache(node, prompt, "ignored")
    with patch("rob2_pipeline.llm_client.get_llm", return_value=object()), patch(
        "rob2_pipeline.llm_client.call_llm", return_value="live"
    ) as call_mock:
        response, _, _ = call_node_llm({}, prompt, node)

    assert response == "live"
    assert call_mock.call_count == 1
    assert read_cache(node, prompt) is None
