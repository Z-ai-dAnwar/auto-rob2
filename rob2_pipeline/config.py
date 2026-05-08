import os
from dataclasses import dataclass

from dotenv import load_dotenv

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
    value = os.getenv("ROB2_EFFECT_OF_INTEREST", DEFAULT_EFFECT_OF_INTEREST)
    if value not in ("ITT", "per-protocol"):
        raise ValueError("ROB2_EFFECT_OF_INTEREST must be either 'ITT' or 'per-protocol'")
    return value


_llm_cfg = get_llm_config()
LLM_MODEL = _llm_cfg.model
LLM_TEMPERATURE = _llm_cfg.temperature
LLM_MAX_TOKENS = _llm_cfg.max_tokens
RPM_LIMIT = _llm_cfg.rpm_limit
RPD_LIMIT = _llm_cfg.rpd_limit

PROVIDER_NAME = os.getenv("ROB2_PROVIDER", "openrouter")


def build_provider():
    load_dotenv()
    from rob2_pipeline.providers import get_provider

    common = dict(model=LLM_MODEL, temperature=LLM_TEMPERATURE, max_tokens=LLM_MAX_TOKENS)
    if PROVIDER_NAME == "openrouter":
        return get_provider(
            "openrouter",
            api_key=os.environ["OPENROUTER_API_KEY"],
            rpm_limit=RPM_LIMIT,
            rpd_limit=RPD_LIMIT,
            **common,
        )
    elif PROVIDER_NAME == "anthropic":
        return get_provider("anthropic", api_key=os.environ["ANTHROPIC_API_KEY"], **common)
    elif PROVIDER_NAME == "openai":
        return get_provider("openai", api_key=os.environ["OPENAI_API_KEY"], **common)
    raise ValueError(f"Unknown ROB2_PROVIDER: {PROVIDER_NAME!r}")
