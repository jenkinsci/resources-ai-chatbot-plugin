"""
Llama.cpp Provider Implementation

Implements the LLMProvider interface using a local model.

This provider uses llama-cpp-python to run inference 
on quantized models (GGUF format).
"""


from api.config.loader import CONFIG
from api.models.llm_provider import LLMProvider
from utils import LoggerFactory
import logging

try:
    from threading import Lock
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    Lock = None
    Llama = None
    logging.warning("llama-cpp-python is not installed. LlamaCppProvider will be disabled.")


llm_config = CONFIG["llm"]
logger = LoggerFactory.instance().get_logger("llm")

# pylint: disable=too-few-public-methods
from typing import AsyncGenerator
import asyncio

class LlamaCppProvider(LLMProvider if LLAMA_CPP_AVAILABLE else object):
    """
    LLMProvider implementation for local llama.cpp models, or fallback if unavailable.
    """
    def __init__(self, *args, **kwargs):
        if LLAMA_CPP_AVAILABLE:
            self.llm = Llama(
                model_path=llm_config["model_path"],
                n_ctx=llm_config["context_length"],
                n_threads=llm_config["threads"],
                n_gpu_layers=llm_config["gpu_layers"],
                verbose=llm_config["verbose"]
            )
            self.lock = Lock()
        else:
            logger.warning("llama-cpp-python is not installed. LlamaCppProvider is disabled.")
            self.llm = None
            self.lock = None

    def generate(self, prompt: str, max_tokens: int) -> str:
        if not LLAMA_CPP_AVAILABLE:
            raise ImportError("llama-cpp-python is not installed. LlamaCppProvider is unavailable.")
        try:
            with self.lock:
                output = self.llm(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    echo=False
                )
            return output["choices"][0]["text"].strip()
        except ValueError as e:
            logger.error("Invalid model configuration: %s", e)
            raise RuntimeError("LLM model could not be initialized. Check the model path.") from e
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.error("Unexpected error during LLM generation: %s", e)
            return "Sorry, something went wrong during generation."

    async def generate_stream(self, prompt: str, max_tokens: int) -> AsyncGenerator[str, None]:
        """
        Generate streaming response from llama-cpp-python model.
        Args:
            prompt: Input prompt for the model
            max_tokens: Maximum tokens to generate
        Yields:
            str: Individual tokens as generated
        """
        if not LLAMA_CPP_AVAILABLE:
            yield "[llama-cpp-python is not installed. No LLM streaming available.]"
            return
        try:
            def _stream_generator():
                with self.lock:
                    return self.llm(
                        prompt=prompt,
                        max_tokens=max_tokens,
                        echo=False,
                        stream=True
                    )

            loop = asyncio.get_event_loop()
            stream = await loop.run_in_executor(None, _stream_generator)

            for chunk in stream:
                if "choices" in chunk and len(chunk["choices"]) > 0:
                    delta = chunk["choices"][0].get("delta", {})
                    if "content" in delta:
                        yield delta["content"]
                    elif "text" in chunk["choices"][0]:
                        yield chunk["choices"][0]["text"]
        except ValueError as e:
            logger.error(f"Invalid model configuration: {e}")
            yield "Sorry, model configuration error."
        except Exception as e:
            logger.error(
                f"Unexpected error during LLM streaming. "
                f"Prompt preview: {prompt[:100]}...",
                exc_info=True
            )
            yield "Sorry, an unexpected error occurred."

llm_provider = None if CONFIG["is_test_mode"] else LlamaCppProvider()
