"""Request-scoped selection of local and hosted LLM providers."""

import os
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from dotenv import load_dotenv

from api.config.providers import ProviderDefinition, load_provider_catalog
from api.config.env_sync import DEFAULT_ENV_PATH, sync_provider_env
from api.models.llm_provider import LLMProvider
from api.models.litellm import LiteLLMProvider

_CURRENT_PROVIDER: ContextVar[LLMProvider | None] = ContextVar(
    "current_llm_provider",
    default=None,
)

@dataclass(frozen=True)
class HostedProviderConfig:
    """Configuration needed to construct one hosted provider."""

    model: str
    api_key: str | None = None
    api_base: str | None = None
    timeout: int = 60

    def __post_init__(self) -> None:
        if not self.model:
            raise ValueError("A hosted provider model is required.")


ProviderFactory = Callable[[HostedProviderConfig], LLMProvider]


def _build_litellm_provider(config: HostedProviderConfig) -> LLMProvider:
    """Build a LiteLLM provider from request configuration."""
    return LiteLLMProvider(
        model=config.model,
        api_key=config.api_key,
        api_base=config.api_base,
        timeout=config.timeout,
    )


def build_provider_manager(
    local_provider: LLMProvider,
    provider_catalog: tuple[ProviderDefinition, ...] | None = None,
    environment: Mapping[str, str] | None = None,
) -> "ProviderManager":
    """Build a provider manager from the catalog and environment."""
    uses_default_catalog = provider_catalog is None
    catalog = load_provider_catalog() if uses_default_catalog else provider_catalog
    if uses_default_catalog and environment is None:
        sync_provider_env(catalog)
    if environment is None:
        load_dotenv(DEFAULT_ENV_PATH, override=False)
    env = os.environ if environment is None else environment
    hosted_providers = {
        provider.id: HostedProviderConfig(
            model=provider.model,
            api_key=env.get(provider.api_key_env),
        )
        for provider in catalog
        if provider.id != "local"
    }
    return ProviderManager(local_provider, hosted_providers)


class ProviderManager:
    """Resolve and activate providers for an individual request."""

    def __init__(
        self,
        local_provider: LLMProvider,
        hosted_providers: Mapping[str, HostedProviderConfig] | None = None,
        provider_factory: ProviderFactory = _build_litellm_provider,
    ) -> None:
        self._local_provider = local_provider
        self._hosted_providers = dict(hosted_providers or {})
        self._provider_factory = provider_factory

    def resolve(self, provider_id: str = "local") -> LLMProvider:
        """Resolve one provider without changing request-local state."""
        if provider_id == "local":
            return self._local_provider

        config = self._hosted_providers.get(provider_id)
        if config is None:
            raise ValueError(f"Unsupported LLM provider: {provider_id}")
        if not config.api_key:
            raise ValueError(
                f"No API key configured for provider: {provider_id}. "
                f"Set {provider_id.upper()}_API_KEY."
            )

        return self._provider_factory(config)

    @contextmanager
    def activate(self, provider_id: str = "local") -> Iterator[LLMProvider]:
        """Activate a provider and restore the previous provider afterwards."""
        with self.activate_provider(self.resolve(provider_id)) as provider:
            yield provider

    @contextmanager
    def activate_provider(self, provider: LLMProvider) -> Iterator[LLMProvider]:
        """Activate an already-resolved provider for the current request."""
        token = _CURRENT_PROVIDER.set(provider)
        try:
            yield provider
        finally:
            _CURRENT_PROVIDER.reset(token)


def get_current_provider() -> LLMProvider | None:
    """Return the provider active in the current request context."""
    return _CURRENT_PROVIDER.get()
