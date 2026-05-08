from .base import LLMProvider, LLMResponse


def get_provider(provider_name: str, **kwargs) -> LLMProvider:
    if provider_name == "openrouter":
        from .openrouter import OpenRouterProvider

        return OpenRouterProvider(**kwargs)
    elif provider_name == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider(**kwargs)
    elif provider_name == "openai":
        from .openai import OpenAIProvider

        return OpenAIProvider(**kwargs)
    raise ValueError(f"Unknown provider: {provider_name!r}. Valid: openrouter, anthropic, openai")
