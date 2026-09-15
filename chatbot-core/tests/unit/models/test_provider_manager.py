"""Tests for request-scoped provider selection."""

from types import SimpleNamespace

import pytest

from api.models.provider_manager import (
    HostedProviderConfig,
    ProviderManager,
    get_current_provider,
)


class FakeProvider:
    """Small provider double that satisfies the common provider contract."""

    def generate(self, prompt: str, max_tokens: int) -> str:
        """Return the received values for assertions."""
        return f"{prompt}:{max_tokens}"

    async def generate_stream(self, prompt: str, max_tokens: int):
        """Yield the received values for assertions."""
        yield f"{prompt}:{max_tokens}"


def test_resolve_returns_local_provider():
    """The local provider is the explicit default."""
    local_provider = FakeProvider()
    manager = ProviderManager(local_provider)

    assert manager.resolve() is local_provider
    assert manager.resolve("local") is local_provider


def test_resolve_builds_hosted_provider_from_configuration():
    """Hosted configuration is passed to the provider factory."""
    config = HostedProviderConfig(
        model="groq/llama-3.3-70b-versatile",
        api_key="test-key",
    )
    created_configs = []

    def provider_factory(provider_config):
        created_configs.append(provider_config)
        return SimpleNamespace(name="hosted")

    manager = ProviderManager(
        FakeProvider(),
        {"groq": config},
        provider_factory=provider_factory,
    )

    provider = manager.resolve("groq")

    assert provider.name == "hosted"
    assert created_configs == [config]


def test_resolve_rejects_unknown_provider():
    """Provider selection never silently falls back to the local model."""
    manager = ProviderManager(FakeProvider())

    with pytest.raises(ValueError, match="Unsupported LLM provider: unknown"):
        manager.resolve("unknown")


def test_activate_restores_previous_provider():
    """Provider context is restored after a request completes."""
    local_provider = FakeProvider()
    hosted_provider = FakeProvider()
    manager = ProviderManager(
        local_provider,
        {"hosted": HostedProviderConfig(model="test/model", api_key="key")},
        provider_factory=lambda _config: hosted_provider,
    )

    assert get_current_provider() is None
    with manager.activate("hosted") as active_provider:
        assert active_provider is hosted_provider
        assert get_current_provider() is hosted_provider
    assert get_current_provider() is None


def test_hosted_configuration_requires_api_key():
    """Hosted providers cannot be created without request credentials."""
    with pytest.raises(ValueError, match="API key is required"):
        HostedProviderConfig(model="test/model", api_key="")
