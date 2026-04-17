"""
Providers package - A collection of LLM provider implementations.

Usage:
    from providers import OpenAIProvider, AnthropicProvider, OllamaProvider

    # Initialize a provider
    openai = OpenAIProvider(api_key="your-key-here")

    # Send a chat request
    from providers import ChatMessage
    messages = [
        ChatMessage(role="user", content="Hello!"),
    ]
    response = await openai.chat(messages)
    print(response.content)
"""
import asyncio

from .base import LLMProvider, ChatMessage, ChatResponse
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider
from .ollama import OllamaProvider

# Provider registry for dynamic discovery
PROVIDERS = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
}

__all__ = [
    # Base classes
    "LLMProvider",
    "ChatMessage",
    "ChatResponse",

    # Providers
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",

    # Registry
    "PROVIDERS",
]


def get_provider(name: str, **kwargs) -> LLMProvider:
    """
    Factory function to create a provider instance by name.

    Args:
        name: Provider identifier ("openai", "anthropic", "lmstudio", "ollama")
        **kwargs: Arguments passed to the provider constructor

    Returns:
        Configured LLMProvider instance

    Raises:
        ValueError: If provider name is not recognized
    """
    if name.lower() not in PROVIDERS:
        available = list(PROVIDERS.keys())
        raise ValueError(
            f"Unknown provider '{name}'. Available providers: {available}"
        )

    provider_class = PROVIDERS[name.lower()]
    return provider_class(**kwargs)