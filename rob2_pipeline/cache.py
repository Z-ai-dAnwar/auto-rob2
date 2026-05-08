import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

CACHE_DIR = Path(".rob2_cache")
DEFAULT_TTL_DAYS = 7


def _use_cache() -> bool:
    return os.getenv("ROB2_USE_CACHE") == "1"


def _ttl_days() -> int:
    raw = os.getenv("ROB2_CACHE_TTL_DAYS")
    if not raw:
        return DEFAULT_TTL_DAYS
    try:
        return max(int(raw), 0)
    except ValueError:
        return DEFAULT_TTL_DAYS


def _cache_key(node_name: str, prompt_text: str) -> str:
    raw = f"{node_name}:{prompt_text}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return digest[:16]


def _cache_path(prompt_hash: str) -> Path:
    return CACHE_DIR / f"{prompt_hash}.json"


def _is_expired(cached_at_iso: str, ttl_days: int) -> bool:
    try:
        cached_at = datetime.fromisoformat(cached_at_iso)
    except ValueError:
        return True
    if cached_at.tzinfo is None:
        cached_at = cached_at.replace(tzinfo=timezone.utc)
    expires_at = cached_at + timedelta(days=ttl_days)
    return datetime.now(timezone.utc) > expires_at


def read_cache(node_name: str, prompt_text: str) -> str | None:
    if not _use_cache():
        return None
    prompt_hash = _cache_key(node_name, prompt_text)
    path = _cache_path(prompt_hash)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    ttl_days = _ttl_days()
    if _is_expired(payload.get("cached_at_iso", ""), ttl_days):
        return None
    if payload.get("prompt_hash") != prompt_hash:
        return None
    if payload.get("node_name") != node_name:
        return None
    return payload.get("response")


def write_cache(node_name: str, prompt_text: str, response: str) -> None:
    if not _use_cache():
        return
    prompt_hash = _cache_key(node_name, prompt_text)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "prompt_hash": prompt_hash,
        "node_name": node_name,
        "response": response,
        "cached_at_iso": datetime.now(timezone.utc).isoformat(),
    }
    _cache_path(prompt_hash).write_text(json.dumps(payload, indent=2), encoding="utf-8")


__all__ = ["read_cache", "write_cache"]
