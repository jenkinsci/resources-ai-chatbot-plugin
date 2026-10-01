"""Tests for the LiteLLM provider adapter."""

import asyncio
from types import SimpleNamespace

import pytest

from api.models.litellm import LiteLLMProvider


def test_provider_rejects_missing_model():
    """A hosted provider cannot be created without a model path."""
    with pytest.raises(ValueError, match="model is required"):
        LiteLLMProvider(model="")


def test_generate_passes_request_configuration(monkeypatch):
    """Synchronous generation forwards model and request-scoped credentials."""
    calls = []

    def completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="reply"))]
        )

    monkeypatch.setattr(
        "api.models.litellm.provider.completion",
        completion,
    )
    provider = LiteLLMProvider(
        model="groq/llama-3.3-70b-versatile",
        api_key="test-key",
        api_base="https://example.test/v1",
        timeout=30,
    )

    result = provider.generate("hello", max_tokens=12)

    assert result == "reply"
    assert calls == [{
        "model": "groq/llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": "hello"}],
        "api_key": "test-key",
        "api_base": "https://example.test/v1",
        "max_tokens": 12,
        "timeout": 30,
    }]


def test_generate_stream_yields_content(monkeypatch):
    """Streaming generation yields only non-empty content deltas."""
    chunks = [
        SimpleNamespace(choices=[]),
        SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="one"))]
        ),
        SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content=" two"))]
        ),
    ]

    async def stream_response(**_kwargs):
        for chunk in chunks:
            yield chunk

    async def acompletion(**_kwargs):
        return stream_response()

    monkeypatch.setattr(
        "api.models.litellm.provider.acompletion",
        acompletion,
    )
    provider = LiteLLMProvider(model="gemini/gemini-3-flash-preview")

    async def collect_tokens():
        return [
            token
            async for token in provider.generate_stream("hello", max_tokens=12)
        ]

    result = asyncio.run(collect_tokens())

    assert result == ["one", " two"]
