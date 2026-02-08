"""
Llama.cpp Provider Implementation

Implements the LLMProvider interface using a local model.

This provider uses llama-cpp-python to run inference
on quantized models (GGUF format).
"""

# =========================
# Standard library imports
# =========================
import asyncio
import logging
from threading import Lock
from typing import AsyncGenerator

# =========================
# Third-party / local imports
# =========================
from api.config.loader import CONFIG
from api.models.llm_provider import LLMProvider
from utils import LoggerFactory
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    Llama = None
    logging.warning(
        "llama-cpp-python is not installed. "
        "LlamaCppProvider will be disabled."
    )

llm_config = CONFIG["llm"]
logger = LoggerFactory.instance().get_logger("llm")


class LlamaCppProvider(LLMProvider if LLAMA_CPP_AVAILABLE else object):
    """
    LLMProvider implementation for local llama.cpp models,
    or a safe fallback if llama-cpp is unavailable.
    """

    def __init__(self, *_args, **_kwargs):
        if not LLAMA_CPP_AVAILABLE:
            logger.warning(
                "llama-cpp-python is not installed. "
                "LlamaCppProvider is disabled."
            )
            self.llm = None
            self.lock = None
            return

        self.llm = Llama(
            model_path=llm_config["model_path"],
            n_ctx=llm_config["context_length"],
            n_threads=llm_config["threads"],
            n_gpu_layers=llm_config["gpu_layers"],
            verbose=llm_config["verbose"],
        )
        self.lock = Lock()

    def generate(self, prompt: str, max_tokens: int) -> str:
        if not LLAMA_CPP_AVAILABLE:
            raise ImportError(
                "llama-cpp-python is not installed. "
                "LlamaCppProvider is unavailable."
            )

        try:
            with self.lock:
                output = self.llm(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    echo=False,
                )
            return output["choices"][0]["text"].strip()

        except ValueError as exc:
            logger.error("Invalid model configuration: %s", exc)
            raise RuntimeError(
                "LLM model could not be initialized. "
                "Check the model path."
            ) from exc

        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error(
                "Unexpected error during LLM generation: %s",
                exc,
            )
            return "Sorry, something went wrong during generation."

    async def generate_stream(
        self, prompt: str, max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response from llama.cpp.

        Args:
            prompt: Input prompt for the model
            max_tokens: Maximum tokens to generate
        """
        if not LLAMA_CPP_AVAILABLE:
            yield (
                "[llama-cpp-python is not installed. "
                "No LLM streaming available.]"
            )
            return

        try:
            def _stream_generator():
                with self.lock:
                    return self.llm(
                        prompt=prompt,
                        max_tokens=max_tokens,
                        echo=False,
                        stream=True,
                    )

            loop = asyncio.get_event_loop()
            stream = await loop.run_in_executor(None, _stream_generator)

            for chunk in stream:
                choices = chunk.get("choices", [])
                if not choices:
                    continue

                choice = choices[0]
                delta = choice.get("delta", {})
                if "content" in delta:
                    yield delta["content"]
                elif "text" in choice:
                    yield choice["text"]

        except ValueError as exc:
            logger.error("Invalid model configuration: %s", exc)
            yield "Sorry, model configuration error."

        except Exception :  # pylint: disable=broad-exception-caught
            logger.error(
                "Unexpected error during LLM streaming. "
                "Prompt preview: %s...",
                prompt[:100],
                exc_info=True,
            )
            yield "Sorry, an unexpected error occurred."


llm_provider = None if CONFIG["is_test_mode"] else LlamaCppProvider()
