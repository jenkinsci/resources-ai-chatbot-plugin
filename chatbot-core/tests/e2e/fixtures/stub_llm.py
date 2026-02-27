"""
StubLLMProvider — a real LLMProvider implementation that returns canned
responses without loading any model weights.

Used by E2E tests so the full call chain executes:
    router → service → provider.generate() → memory → persist → disk

Only inference is swapped; everything else is production code.
"""

from api.models.llm_provider import LLMProvider

_DEFAULT_REPLY = "This is a stub LLM response for E2E testing."


class StubLLMProvider(LLMProvider):
    """Deterministic LLM provider for E2E tests.

    Parameters
    ----------
    reply : str, optional
        The fixed string returned by every ``generate()`` call.
        Defaults to ``_DEFAULT_REPLY``.
    """

    def __init__(self, reply: str = _DEFAULT_REPLY):
        self._reply = reply
        self._call_count = 0

    # --- LLMProvider interface ------------------------------------------------

    def generate(self, prompt: str, max_tokens: int = 512) -> str:  # noqa: ARG002
        """Return the canned reply, ignoring *prompt* and *max_tokens*."""
        self._call_count += 1
        return self._reply

    # --- Test helpers ---------------------------------------------------------

    @property
    def call_count(self) -> int:
        """How many times ``generate()`` has been called."""
        return self._call_count

    def reset(self) -> None:
        """Reset the call counter (useful between tests)."""
        self._call_count = 0
