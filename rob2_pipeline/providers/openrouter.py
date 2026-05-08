import threading
import time
from collections import deque

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openrouter import ChatOpenRouter
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .base import LLMProvider, LLMResponse


class OpenRouterProvider(LLMProvider):
    def __init__(
        self,
        api_key,
        model,
        temperature=0,
        max_tokens=2000,
        rpm_limit=18,
        rpd_limit=190,
    ):
        self._model = model
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.rpm_limit = rpm_limit
        self.rpd_limit = rpd_limit
        self._minute_window = deque()
        self._day_window = deque()
        self._lock = threading.Lock()
        self.client = ChatOpenRouter(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @property
    def model_id(self):
        return self._model

    def _wait_for_rate_limit(self):
        with self._lock:
            now = time.time()
            self._minute_window = deque(t for t in self._minute_window if now - t < 60)
            self._day_window = deque(t for t in self._day_window if now - t < 86400)

            if len(self._day_window) >= self.rpd_limit:
                sleep_time = 86400 - (now - self._day_window[0]) + 1
                print(f"Daily limit approached. Sleeping {sleep_time:.0f}s")
                time.sleep(sleep_time)

            if len(self._minute_window) >= self.rpm_limit:
                sleep_time = 60 - (now - self._minute_window[0]) + 1
                time.sleep(sleep_time)

            self._minute_window.append(time.time())
            self._day_window.append(time.time())

    @retry(
        wait=wait_exponential(multiplier=2, min=5, max=120),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((Exception,)),
    )
    def complete(self, system: str, user: str) -> LLMResponse:
        self._wait_for_rate_limit()
        start = time.perf_counter()
        response = self.client.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        latency_ms = (time.perf_counter() - start) * 1000
        usage = response.usage_metadata or {}
        return LLMResponse(
            content=response.content,
            model=self._model,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            latency_ms=latency_ms,
        )
