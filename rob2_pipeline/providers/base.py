from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cached: bool = False
    # Some providers (e.g. gpt-oss-120b through OpenRouter) return the model's
    # chain-of-thought in a separate field. Capture it here so the trace can
    # show whether the model actually reasoned over the retrieved chunks.
    # Stays None for providers that do not emit reasoning.
    reasoning_content: str | None = None


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str) -> LLMResponse: ...

    @property
    @abstractmethod
    def model_id(self) -> str: ...
