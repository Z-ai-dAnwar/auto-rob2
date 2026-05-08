import os
from dataclasses import dataclass

from rob2_pipeline.constants import DEFAULT_EFFECT_OF_INTEREST


@dataclass(frozen=True)
class LLMConfig:
    model: str = "openai/gpt-oss-120b:free"
    temperature: int = 0
    max_tokens: int = 2000
    rpm_limit: int = 18
    rpd_limit: int = 190


def get_llm_config() -> LLMConfig:
    return LLMConfig(
        model=os.getenv("ROB2_MODEL", "openai/gpt-oss-120b:free"),
        temperature=int(os.getenv("ROB2_TEMPERATURE", "0")),
        max_tokens=int(os.getenv("ROB2_MAX_TOKENS", "2000")),
        rpm_limit=int(os.getenv("ROB2_RPM_LIMIT", "18")),
        rpd_limit=int(os.getenv("ROB2_RPD_LIMIT", "190")),
    )


def get_default_effect_of_interest() -> str:
    return os.getenv("ROB2_EFFECT_OF_INTEREST", DEFAULT_EFFECT_OF_INTEREST)
