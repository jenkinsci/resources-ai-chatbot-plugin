"""LiteLLM provider implementation for hosted and OpenAI-compatible models."""

from collections.abc import AsyncGenerator
from typing import Any

from litellm import acompletion, completion

from api.models.llm_provider import LLMProvider

class LiteLLMProvider(LLMProvider):
    """Generate responses through LiteLLM's unified completion interface."""

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        api_base: str | None = None,
        timeout: int = 60,
    ) -> None:
        if not model:
            raise ValueError("A LiteLLM model is required.")
        if timeout <= 0:
            raise ValueError("LiteLLM timeout must be greater than zero.")

        self.model = model
        self.api_key = api_key
        self.api_base = api_base
        self.timeout = timeout

    def _request_kwargs(self, prompt: str, max_tokens: int) -> dict[str, Any]:
        """Build request arguments shared by synchronous and streaming calls."""
        request_kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "timeout": self.timeout,
        }
        if self.api_key is not None:
            request_kwargs["api_key"] = self.api_key
        if self.api_base is not None:
            request_kwargs["api_base"] = self.api_base
        if self.model.startswith("groq/qwen/"):
            request_kwargs["reasoning_effort"] = "none"
        return request_kwargs

    def generate(self, prompt: str, max_tokens: int) -> str:
        """Generate a complete response through LiteLLM."""
        response = completion(**self._request_kwargs(prompt, max_tokens))
        choices = getattr(response, "choices", None) or []
        if not choices:
            return ""

        message = getattr(choices[0], "message", None)
        return getattr(message, "content", None) or ""

    async def generate_stream(
        self, prompt: str, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """Generate a response token-by-token through LiteLLM."""
        response = await acompletion(
            **self._request_kwargs(prompt, max_tokens),
            stream=True,
        )

        async for chunk in response:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue

            delta = getattr(choices[0], "delta", None)
            content = getattr(delta, "content", None)
            if content:
                yield content
