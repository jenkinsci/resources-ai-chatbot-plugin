"""
Llama.cpp Provider Implementation

Implements the LLMProvider interface using a local model.

This provider uses llama-cpp-python to run inference 
on quantized models (GGUF format).
"""

from threading import Lock
from typing import AsyncGenerator
from llama_cpp import Llama
from api.config.loader import CONFIG
from api.models.llm_provider import LLMProvider
from utils import LoggerFactory
import asyncio

llm_config = CONFIG["llm"]
logger = LoggerFactory.instance().get_logger("llm")

# pylint: disable=too-few-public-methods
class LlamaCppProvider(LLMProvider):
    """
    LLMProvider implementation for local llama.cpp models.
    """
    def __init__(self):
        """
        Initializes the Llama model with configuration from config.yml.
        Sets up a lock to ensure thread-safe usage.
        """
        self.llm = Llama(
            model_path=llm_config["model_path"],
            n_ctx=llm_config["context_length"],
            n_threads=llm_config["threads"],
            n_gpu_layers=llm_config["gpu_layers"],
            verbose=llm_config["verbose"]
        )
        self.lock = Lock()

    def generate(self, prompt: str, max_tokens: int) -> str:
        """
        Generate a response from the model given a prompt.

        Args:
            prompt (str): Prompt to feed into the model.
            max_tokens (int): Maximum number of tokens to generate.

        Returns:
            str: The generated text response.
        """
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
        Generate a streaming response from the model given a prompt.

        Args:
            prompt (str): Prompt to feed into the model.
            max_tokens (int): Maximum number of tokens to generate.

        Yields:
            str: Individual tokens as they're generated.
        """
        try:
            def _stream_generator():
                with self.lock:
                    return self.llm(
                        prompt=prompt,
                        max_tokens=max_tokens,
                        echo=False,
                        stream=True
                    )
            
            # Run in thread pool to avoid blocking
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
            logger.error("Invalid model configuration: %s", e)
            yield "Sorry, model configuration error."
        except Exception as e:
            logger.error("Unexpected error during LLM streaming: %s", e)
            yield "Sorry, something went wrong during generation."

llm_provider = None if CONFIG["is_test_mode"] else LlamaCppProvider()
