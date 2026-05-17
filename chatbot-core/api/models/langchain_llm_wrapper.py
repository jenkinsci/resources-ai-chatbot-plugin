"""LangChain LLM proxy wrapper to avoid reloading Llama.cpp."""
from typing import Any, List, Optional
from langchain_core.language_models.llms import LLM
from api.models.llama_cpp_provider import llm_provider

class CustomLangchainLLM(LLM):
    """Custom LangChain LLM wrapper that proxies to llm_provider."""
    max_tokens: int = 256

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> str:
        """Call the local LlamaCppProvider directly."""
        if llm_provider is None:
            return "[Summary ignored: LLM is offline]"
        return llm_provider.generate(prompt, max_tokens=self.max_tokens)

    @property
    def _llm_type(self) -> str:
        """Return the type of the LLM wrapper."""
        return "custom_llama_cpp"
