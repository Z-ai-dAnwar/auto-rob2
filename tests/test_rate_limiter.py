import time

import pytest

from rob2_pipeline.providers._rate_limiter import SlidingWindowRateLimiter


def test_estimate_input_tokens_returns_buffered_quotient():
    estimate = SlidingWindowRateLimiter.estimate_input_tokens("abc", "defghi")
    assert estimate == (3 + 6) // 3 + 100


def test_wait_for_slot_returns_immediately_when_no_limits_set():
    limiter = SlidingWindowRateLimiter()
    start = time.perf_counter()
    limiter.wait_for_slot(estimated_tokens=10_000)
    assert time.perf_counter() - start < 0.1


def test_wait_for_slot_records_rpm_under_threshold():
    limiter = SlidingWindowRateLimiter(rpm_limit=10)
    for _ in range(5):
        limiter.wait_for_slot()
    assert len(limiter._minute_requests) == 5


def test_rpd_limit_uses_logging_warning_not_print(monkeypatch, caplog):
    limiter = SlidingWindowRateLimiter(rpd_limit=1)
    base = 3_000_000.0
    fake_now = {"t": base}

    def fake_time():
        return fake_now["t"]

    def fake_sleep(seconds):
        fake_now["t"] += seconds

    monkeypatch.setattr("rob2_pipeline.providers._rate_limiter.time.time", fake_time)
    monkeypatch.setattr("rob2_pipeline.providers._rate_limiter.time.sleep", fake_sleep)

    limiter.wait_for_slot()
    with caplog.at_level("WARNING", logger="rob2_pipeline.providers._rate_limiter"):
        limiter.wait_for_slot()
    assert any(
        "Daily request limit approached" in rec.message for rec in caplog.records
    )


def test_wait_for_slot_blocks_when_rpm_exceeded(monkeypatch):
    limiter = SlidingWindowRateLimiter(rpm_limit=2)
    base = 1_000_000.0
    fake_now = {"t": base}

    def fake_time():
        return fake_now["t"]

    sleeps: list[float] = []

    def fake_sleep(seconds):
        sleeps.append(seconds)
        fake_now["t"] += seconds

    monkeypatch.setattr("rob2_pipeline.providers._rate_limiter.time.time", fake_time)
    monkeypatch.setattr("rob2_pipeline.providers._rate_limiter.time.sleep", fake_sleep)

    limiter.wait_for_slot()
    fake_now["t"] += 1
    limiter.wait_for_slot()
    fake_now["t"] += 1
    limiter.wait_for_slot()

    assert len(sleeps) == 1
    assert 55 <= sleeps[0] <= 60


def test_wait_for_slot_blocks_when_tpm_exceeded(monkeypatch):
    limiter = SlidingWindowRateLimiter(tpm_limit=1000)
    base = 2_000_000.0
    fake_now = {"t": base}

    def fake_time():
        return fake_now["t"]

    sleeps: list[float] = []

    def fake_sleep(seconds):
        sleeps.append(seconds)
        fake_now["t"] += seconds

    monkeypatch.setattr("rob2_pipeline.providers._rate_limiter.time.time", fake_time)
    monkeypatch.setattr("rob2_pipeline.providers._rate_limiter.time.sleep", fake_sleep)

    limiter.wait_for_slot(estimated_tokens=600)
    fake_now["t"] += 1
    limiter.wait_for_slot(estimated_tokens=500)

    assert len(sleeps) == 1
    assert 55 <= sleeps[0] <= 60


def test_prune_drops_expired_entries():
    limiter = SlidingWindowRateLimiter(rpm_limit=10, tpm_limit=1000)
    old = time.time() - 120
    limiter._minute_requests.append(old)
    limiter._day_requests.append(old)
    limiter._minute_tokens.append((old, 500))
    limiter._prune(time.time())
    assert not limiter._minute_requests
    assert not limiter._minute_tokens
    assert limiter._day_requests


def test_is_rate_limit_error_handles_429():
    from rob2_pipeline.providers.anthropic import _is_rate_limit_error

    class FakeRateLimitError(Exception):
        status_code = 429

    assert _is_rate_limit_error(FakeRateLimitError("Too many requests"))
    assert _is_rate_limit_error(RuntimeError("429: rate limit exceeded"))
    assert not _is_rate_limit_error(RuntimeError("connection refused"))
    assert not _is_rate_limit_error(ValueError("bad config"))


def test_openrouter_uses_shared_rate_limiter(monkeypatch):
    fake_client_calls: list[tuple[str, str]] = []

    class FakeMessage:
        def __init__(self, content):
            self.content = content
            self.usage_metadata = {"input_tokens": 10, "output_tokens": 5}
            self.additional_kwargs = {}

    class FakeClient:
        def invoke(self, messages):
            fake_client_calls.append((messages[0].content, messages[1].content))
            return FakeMessage("ok")

    monkeypatch.setattr(
        "rob2_pipeline.providers.openrouter.ChatOpenRouter",
        lambda **_: FakeClient(),
    )

    from rob2_pipeline.providers.openrouter import OpenRouterProvider

    provider = OpenRouterProvider(api_key="x", model="test/model")
    assert isinstance(provider._rate_limiter, SlidingWindowRateLimiter)
    provider.complete(system="sys", user="msg")
    assert fake_client_calls == [("sys", "msg")]


def test_anthropic_provider_estimates_and_waits(monkeypatch):
    class FakeMessage:
        def __init__(self):
            self.content = "ok"
            self.response_metadata = {"usage": {"input_tokens": 12, "output_tokens": 7}}
            self.additional_kwargs = {}

    class FakeClient:
        def __init__(self):
            self.invoked_with = None

        def invoke(self, messages):
            self.invoked_with = messages
            return FakeMessage()

    fake_client = FakeClient()
    monkeypatch.setattr(
        "langchain_anthropic.ChatAnthropic",
        lambda **_: fake_client,
    )

    from rob2_pipeline.providers.anthropic import AnthropicProvider

    provider = AnthropicProvider(api_key="x", model="claude-test")
    assert provider._rate_limiter.rpm_limit == 40
    assert provider._rate_limiter.tpm_limit == 30_000

    response = provider.complete(system="abc", user="defghi")
    assert response.content == "ok"
    assert fake_client.invoked_with is not None
