"""Shared sliding-window rate limiter for LLM providers.

Tracks three independent limits in 60s / 86400s windows:
- RPM (requests per minute)
- RPD (requests per day)
- TPM (input tokens per minute) for Anthropic tiers

Anthropic Tier 1 caps input tokens at 50K/min, not request count.
Pass tpm_limit when constructing for Anthropic; leave None for OpenRouter
(which only enforces request counts).
"""

import logging
import threading
import time
from collections import deque

logger = logging.getLogger(__name__)


class SlidingWindowRateLimiter:
    def __init__(
        self,
        rpm_limit: int | None = None,
        rpd_limit: int | None = None,
        tpm_limit: int | None = None,
    ):
        self.rpm_limit = rpm_limit
        self.rpd_limit = rpd_limit
        self.tpm_limit = tpm_limit
        self._minute_requests: deque[float] = deque()
        self._day_requests: deque[float] = deque()
        self._minute_tokens: deque[tuple[float, int]] = deque()
        self._lock = threading.Lock()

    @staticmethod
    def estimate_input_tokens(system: str, user: str) -> int:
        return (len(system) + len(user)) // 3 + 100

    def wait_for_slot(self, estimated_tokens: int = 0) -> None:
        with self._lock:
            now = time.time()
            self._prune(now)

            if self.rpd_limit is not None and len(self._day_requests) >= self.rpd_limit:
                sleep_time = 86400 - (now - self._day_requests[0]) + 1
                logger.warning(
                    "Daily request limit approached. Sleeping %.0fs", sleep_time
                )
                time.sleep(sleep_time)
                now = time.time()
                self._prune(now)

            if (
                self.rpm_limit is not None
                and len(self._minute_requests) >= self.rpm_limit
            ):
                sleep_time = 60 - (now - self._minute_requests[0]) + 1
                time.sleep(sleep_time)
                now = time.time()
                self._prune(now)

            if self.tpm_limit is not None and estimated_tokens > 0:
                current_tokens = sum(tokens for _, tokens in self._minute_tokens)
                while (
                    current_tokens + estimated_tokens > self.tpm_limit
                    and self._minute_tokens
                ):
                    oldest_ts, _ = self._minute_tokens[0]
                    sleep_time = 60 - (now - oldest_ts) + 1
                    if sleep_time <= 0:
                        break
                    time.sleep(sleep_time)
                    now = time.time()
                    self._prune(now)
                    current_tokens = sum(tokens for _, tokens in self._minute_tokens)

            self._minute_requests.append(now)
            self._day_requests.append(now)
            if self.tpm_limit is not None:
                self._minute_tokens.append((now, estimated_tokens))

    def _prune(self, now: float) -> None:
        while self._minute_requests and now - self._minute_requests[0] >= 60:
            self._minute_requests.popleft()
        while self._day_requests and now - self._day_requests[0] >= 86400:
            self._day_requests.popleft()
        while self._minute_tokens and now - self._minute_tokens[0][0] >= 60:
            self._minute_tokens.popleft()
