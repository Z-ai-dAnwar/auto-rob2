from .base import LLMProvider, LLMResponse as LLMResponse


def get_provider(provider_name: str, **kwargs) -> LLMProvider:
    if provider_name == "openrouter":
        from .openrouter import OpenRouterProvider

        return OpenRouterProvider(**kwargs)
    if provider_name == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider(**kwargs)
    if provider_name == "openai":
        from .openai import OpenAIProvider

        return OpenAIProvider(**kwargs)
    raise ValueError(
        f"Unknown provider: {provider_name!r}. Valid: openrouter, anthropic, openai"
    )
