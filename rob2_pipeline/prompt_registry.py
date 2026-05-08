"""Non-breaking prompt registry layer.

This module provides a central index over prompt templates while preserving
the existing `rob2_pipeline.prompts` constants used across the codebase.
"""

from rob2_pipeline import prompts


PROMPTS: dict[str, str] = {
    "rct_screen": prompts.PROMPT_RCT_SCREEN,
    "preliminary_info": prompts.PROMPT_PRELIMINARY_INFO,
    "domain1": prompts.PROMPT_DOMAIN1,
    "domain2_sq12": prompts.PROMPT_DOMAIN2_SQ12,
    "domain2_conditional": prompts.PROMPT_DOMAIN2_CONDITIONAL,
    "domain2_analysis": prompts.PROMPT_DOMAIN2_ANALYSIS,
    "domain3": prompts.PROMPT_DOMAIN3,
    "domain4": prompts.PROMPT_DOMAIN4,
    "domain5": prompts.PROMPT_DOMAIN5,
}


def get_prompt(name: str) -> str:
    try:
        return PROMPTS[name]
    except KeyError as exc:
        raise KeyError(f"Unknown prompt: {name}") from exc
