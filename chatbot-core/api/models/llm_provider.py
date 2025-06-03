"""
LLM Provider Interface

Defines an abstract class for all callable LLMs.
"""

from abc import ABC, abstractmethod

# pylint: disable=too-few-public-methods
class LLMProvider(ABC):
    """
    Abstract class for LLM providers. 
    A local model or an external API extend/implement it.
    """

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int) -> str:
        """
        Generate a response given a prompt.
        """
