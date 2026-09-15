"""Request-scoped selection of local and hosted LLM providers."""

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

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
    api_key: str
    api_base: str | None = None
    timeout: int = 60

    def __post_init__(self) -> None:
        if not self.model:
            raise ValueError("A hosted provider model is required.")
        if not self.api_key:
            raise ValueError("A hosted provider API key is required.")


ProviderFactory = Callable[[HostedProviderConfig], LLMProvider]


def _build_litellm_provider(config: HostedProviderConfig) -> LLMProvider:
    """Build a LiteLLM provider from request configuration."""
    return LiteLLMProvider(
        model=config.model,
        api_key=config.api_key,
        api_base=config.api_base,
        timeout=config.timeout,
    )


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
