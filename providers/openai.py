"""
OpenAI-compatible provider with custom URL support.
Works with OpenAI, Azure OpenAI, and any OpenAI-compatible API.
"""

import json
from typing import Any, Dict, List, Optional

import httpx

from .base import LLMProvider, ChatMessage, ChatResponse


class OpenAIProvider(LLMProvider):
    """OpenAI provider with custom URL compatibility."""

    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4o-mini"

    def __init__(self,
                 api_key: str,
                 base_url: Optional[str] = None,
                 model: Optional[str] = None,
                 timeout: int = 60,
                 organization: Optional[str] = None,
                 **kwargs: Any):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key (required)
            base_url: Custom base URL for OpenAI-compatible APIs
            model: Default model to use
            timeout: Request timeout in seconds
            organization: OpenAI organization ID (optional)
            **kwargs: Additional options passed to parent class
        """
        super().__init__(api_key=api_key, base_url=base_url, timeout=timeout, **kwargs)

        if not self.api_key:
            raise ValueError("API key is required for OpenAIProvider")

        self._default_model = model or self.DEFAULT_MODEL
        self._organization = organization

    @property
    def name(self) -> str:
        return "OpenAI"

    async def chat(self,
                   messages: List[ChatMessage],
                   model: Optional[str] = None,
                   temperature: float = 1.0,
                   max_tokens: Optional[int] = None,
                   stream: bool = False,
                   **kwargs: Any) -> ChatResponse:
        """Send a chat completion request to OpenAI."""
        self._validate_message_roles(messages)

        url = f"{self.base_url or self.DEFAULT_BASE_URL}/chat/completions"

        # Convert messages to dict format
        message_dicts = [msg.to_dict() for msg in messages]

        payload: Dict[str, Any] = {
            "model": model or self._default_model,
            "messages": message_dicts,
            "temperature": temperature,
            "stream": stream,
            **kwargs
        }

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        headers = self._build_request_headers()
        if self._organization:
            headers["OpenAI-Organization"] = self._organization

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)

        response.raise_for_status()

        data = response.json()

        return ChatResponse(
            content=data["choices"][0]["message"]["content"],
            model=data["model"],
            usage={
                "prompt_tokens": data.get("usage", {}).get("prompt_tokens"),
                "completion_tokens": data.get("usage", {}).get("completion_tokens"),
                "total_tokens": data.get("usage", {}).get("total_tokens")
            },
            raw_response=data
        )

    async def completion(self,
                         prompt: str,
                         model: Optional[str] = None,
                         temperature: float = 1.0,
                         max_tokens: Optional[int] = None,
                         **kwargs: Any) -> ChatResponse:
        """Send a text completion request to OpenAI."""
        # Use chat API with user message for completions (recommended approach)
        messages = [ChatMessage(role="user", content=prompt)]

        return await self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )


__all__ = ["OpenAIProvider"]