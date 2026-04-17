"""
Anthropic Claude provider.
"""

import json
from typing import Any, Dict, List, Optional

import httpx

from .base import LLMProvider, ChatMessage, ChatResponse


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API provider."""

    DEFAULT_BASE_URL = "https://api.anthropic.com"
    DEFAULT_MODEL = "claude-3-5-sonnet-latest"

    def __init__(self,
                 api_key: str,
                 base_url: Optional[str] = None,
                 model: Optional[str] = None,
                 timeout: int = 60,
                 anthropic_version: str = "2023-06-01",
                 **kwargs: Any):
        """
        Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key (required)
            base_url: Custom base URL for the API
            model: Default model to use
            timeout: Request timeout in seconds
            anthropic_version: API version header value
            **kwargs: Additional options passed to parent class
        """
        super().__init__(api_key=api_key, base_url=base_url, timeout=timeout, **kwargs)

        if not self.api_key:
            raise ValueError("API key is required for AnthropicProvider")

        self._default_model = model or self.DEFAULT_MODEL
        self._anthropic_version = anthropic_version

    @property
    def name(self) -> str:
        return "Anthropic"

    async def chat(self,
                   messages: List[ChatMessage],
                   model: Optional[str] = None,
                   temperature: float = 1.0,
                   max_tokens: int = 4096,
                   system_prompt: Optional[str] = None,
                   **kwargs: Any) -> ChatResponse:
        """Send a message request to Anthropic."""
        self._validate_message_roles(messages)

        url = f"{self.base_url or self.DEFAULT_BASE_URL}/v1/messages"

        # Convert messages - Anthropic only uses "user" and "assistant" roles
        anthropic_messages = []
        system_content = None

        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                anthropic_messages.append({
                    "role": "user" if msg.role == "user" else "assistant",
                    "content": msg.content
                })

        # System prompt can come from first message or separate parameter
        final_system_prompt = system_prompt or system_content

        payload: Dict[str, Any] = {
            "model": model or self._default_model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        if final_system_prompt:
            payload["system"] = final_system_prompt

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-Key": self.api_key,
            "Anthropic-Version": self._anthropic_version
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)

        response.raise_for_status()

        data = response.json()

        return ChatResponse(
            content=data["content"][0]["text"],
            model=data["model"],
            usage={
                "input_tokens": data.get("usage", {}).get("input_tokens"),
                "output_tokens": data.get("usage", {}).get("output_tokens")
            },
            raw_response=data
        )

    async def completion(self,
                         prompt: str,
                         model: Optional[str] = None,
                         temperature: float = 1.0,
                         max_tokens: int = 4096,
                         **kwargs: Any) -> ChatResponse:
        """Send a text completion request to Anthropic."""
        messages = [ChatMessage(role="user", content=prompt)]

        return await self.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )


__all__ = ["AnthropicProvider"]