import time

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openrouter import ChatOpenRouter
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ._rate_limiter import SlidingWindowRateLimiter
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
        self._rate_limiter = SlidingWindowRateLimiter(rpm_limit=rpm_limit, rpd_limit=rpd_limit)
        self.client = ChatOpenRouter(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @property
    def model_id(self):
        return self._model

    @retry(
        wait=wait_exponential(multiplier=2, min=5, max=120),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type((Exception,)),
    )
    def complete(self, system: str, user: str) -> LLMResponse:
        self._rate_limiter.wait_for_slot()
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
