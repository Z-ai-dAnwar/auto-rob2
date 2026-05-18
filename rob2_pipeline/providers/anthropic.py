import time

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from ._rate_limiter import SlidingWindowRateLimiter
from .base import LLMProvider, LLMResponse


def _is_rate_limit_error(exc: BaseException) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code == 429:
        return True
    message = str(exc).lower()
    return "rate" in message and ("limit" in message or "429" in message)


class AnthropicProvider(LLMProvider):
    def __init__(
        self,
        api_key,
        model,
        temperature=0,
        max_tokens=2000,
        rpm_limit: int = 40,
        tpm_limit: int = 30_000,
    ):
        from langchain_anthropic import ChatAnthropic

        self._model = model
        self.client = ChatAnthropic(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._rate_limiter = SlidingWindowRateLimiter(rpm_limit=rpm_limit, tpm_limit=tpm_limit)

    @property
    def model_id(self):
        return self._model

    @retry(
        wait=wait_exponential(multiplier=2, min=30, max=120),
        stop=stop_after_attempt(5),
        retry=retry_if_exception(_is_rate_limit_error),
    )
    def complete(self, system, user):
        from langchain_core.messages import HumanMessage, SystemMessage

        estimated_tokens = SlidingWindowRateLimiter.estimate_input_tokens(system, user)
        self._rate_limiter.wait_for_slot(estimated_tokens=estimated_tokens)
        start = time.time()
        r = self.client.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        usage = (r.response_metadata or {}).get("usage", {})
        return LLMResponse(
            r.content,
            self._model,
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
            (time.time() - start) * 1000,
        )
