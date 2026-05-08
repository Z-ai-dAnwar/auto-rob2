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


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str) -> LLMResponse: ...

    @property
    @abstractmethod
    def model_id(self) -> str: ...
