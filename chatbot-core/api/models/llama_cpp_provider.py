"""
Llama.cpp Provider Implementation

Implements the LLMProvider interface using a local model.

This provider uses llama-cpp-python to run inference 
on quantized models (GGUF format).
"""

from threading import Lock
from llama_cpp import Llama
from api.config.loader import CONFIG
from api.models.llm_provider import LLMProvider
from utils import LoggerFactory

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

llm_provider = None if CONFIG["is_test_mode"] else LlamaCppProvider()
