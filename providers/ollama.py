"""
Ollama local provider.
"""

import json
from typing import Any, Dict, List, Optional

import httpx

from .base import LLMProvider, ChatMessage, ChatResponse


class OllamaProvider(LLMProvider):
    """Ollama local server provider."""

    DEFAULT_BASE_URL = "http://localhost:11434"
    DEFAULT_MODEL = "llama3.2"

    def __init__(self,
                 base_url: Optional[str] = None,
                 model: Optional[str] = None,
                 timeout: int = 60,
                 keep_alive: str = "5m",
                 **kwargs: Any):
        """
        Initialize Ollama provider.

        Args:
            base_url: Base URL for the Ollama server (default: http://localhost:11434)
            model: Default model to use
            timeout: Request timeout in seconds
            keep_alive: How long to keep the model loaded after request
            **kwargs: Additional options passed to parent class
        """
        # Ollama doesn't require API key by default
        super().__init__(base_url=base_url, timeout=timeout, **kwargs)

        self._default_model = model or self.DEFAULT_MODEL
        self._keep_alive = keep_alive

    @property
    def name(self) -> str:
        return "Ollama"

    async def chat(self,
                   messages: List[ChatMessage],
                   model: Optional[str] = None,
                   temperature: float = 1.0,
                   num_predict: Optional[int] = None,
                   **kwargs: Any) -> ChatResponse:
        """Send a chat completion request to Ollama."""
        self._validate_message_roles(messages)

        url = f"{self.base_url or self.DEFAULT_BASE_URL}/api/chat"

        # Convert messages - filter out system role if needed, handle separately
        ollama_messages = []
        system_prompt: Optional[str] = None

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                ollama_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

        payload: Dict[str, Any] = {
            "model": model or self._default_model,
            "messages": ollama_messages,
            "options": {
                "temperature": temperature,
                **kwargs.get("options", {})
            },
            "keep_alive": self._keep_alive,
        }

        if num_predict is not None:
            payload["options"]["num_predict"] = num_predict

        if system_prompt:
            # Ollama supports system prompt in options or as first message
            payload.setdefault("messages", []).insert(0, {
                "role": "system",
                "content": system_prompt
            })

        headers = {"Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)

        response.raise_for_status()

        data = response.json()

        return ChatResponse(
            content=data["message"]["content"],
            model=model or self._default_model,
            usage={
                "prompt_eval_count": data.get("eval_count"),
                "total_tokens": data.get("total_duration", 0) // 1_000_000  # Rough estimate
            },
            raw_response=data
        )

    async def completion(self,
                         prompt: str,
                         model: Optional[str] = None,
                         temperature: float = 1.0,
                         num_predict: Optional[int] = None,
                         **kwargs: Any) -> ChatResponse:
        """Send a text completion request to Ollama."""
        url = f"{self.base_url or self.DEFAULT_BASE_URL}/api/generate"

        payload: Dict[str, Any] = {
            "model": model or self._default_model,
            "prompt": prompt,
            "options": {
                "temperature": temperature,
                **kwargs.get("options", {})
            },
            "keep_alive": self._keep_alive,
        }

        if num_predict is not None:
            payload["options"]["num_predict"] = num_predict

        headers = {"Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload, headers=headers)

        response.raise_for_status()

        data = response.json()

        return ChatResponse(
            content=data["response"],
            model=model or self._default_model,
            usage={
                "prompt_eval_count": data.get("eval_count"),
                "total_tokens": data.get("total_duration", 0) // 1_000_000
            },
            raw_response=data
        )

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models on the Ollama server."""
        url = f"{self.base_url or self.DEFAULT_BASE_URL}/api/tags"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)

        response.raise_for_status()

        return response.json().get("models", [])


__all__ = ["OllamaProvider"]