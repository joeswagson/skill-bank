"""
Base LLM Provider abstract class and common types.
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass


@dataclass
class ChatMessage:
    """Represents a single message in a chat conversation."""
    role: str  # "system", "user", "assistant"
    content: str

    def to_dict(self) -> Dict[str, Any]:
        return {"role": self.role, "content": self.content}


@dataclass
class ChatResponse:
    """Represents a response from an LLM provider."""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None  # token counts if available
    raw_response: Optional[Any] = None

    def __str__(self) -> str:
        return self.content


class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    def __init__(self, api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 timeout: int = 60,
                 **kwargs: Any):
        """
        Initialize the provider.

        Args:
            api_key: API key for authentication (may be optional for local providers)
            base_url: Custom base URL for the API endpoint
            timeout: Request timeout in seconds
            **kwargs: Additional provider-specific options
        """
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self._config = kwargs

    @property
    def name(self) -> str:
        """Return the provider name."""
        return self.__class__.__name__

    async def send_message(self,
                           message: ChatMessage,
                           model: Optional[str] = None,
                           temperature: float = 1.0,
                           max_tokens: Optional[int] = None,
                           **kwargs: Any) -> ChatResponse:
        return await self.chat(
            messages=[message],
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs)

    @abstractmethod
    async def chat(self,
                   messages: List[ChatMessage],
                   model: Optional[str] = None,
                   temperature: float = 1.0,
                   max_tokens: Optional[int] = None,
                   **kwargs: Any) -> ChatResponse:
        """
        Send a chat request to the LLM provider.

        Args:
            messages: List of ChatMessage objects representing the conversation
            model: Model identifier (uses default if not specified)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters

        Returns:
            ChatResponse containing the LLM's response
        """
        pass

    @abstractmethod
    async def completion(self,
                         prompt: str,
                         model: Optional[str] = None,
                         temperature: float = 1.0,
                         max_tokens: Optional[int] = None,
                         **kwargs: Any) -> ChatResponse:
        """
        Send a simple text completion request.

        Args:
            prompt: The text to complete
            model: Model identifier (uses default if not specified)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters

        Returns:
            ChatResponse containing the completion
        """
        pass

    def _build_request_headers(self) -> Dict[str, str]:
        """Build common request headers."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _validate_message_roles(self, messages: List[ChatMessage]) -> None:
        """Validate that message roles are valid."""
        valid_roles = {"system", "user", "assistant"}
        for msg in messages:
            if msg.role not in valid_roles:
                raise ValueError(f"Invalid role '{msg.role}'. Must be one of {valid_roles}")


__all__ = ["LLMProvider", "ChatMessage", "ChatResponse"]
