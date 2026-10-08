"""Invocation of the language model, with the fallback handling it needs.

Everything here is about *talking to the provider*: picking the active one,
sanitizing the prompt and turning provider failures into a user-facing message.
The provider to fall back to is injected by the caller so that it stays
patchable on ``api.services.chat_service``.
"""

from typing import AsyncGenerator, Optional

from api.config.loader import CONFIG
from api.models.provider_manager import get_current_provider
from api.tools.sanitizer import sanitize_log_payload, sanitize_logs
from utils import LoggerFactory

logger = LoggerFactory.instance().get_logger("api")
llm_config = CONFIG["llm"]

PROVIDER_UNAVAILABLE_MESSAGE = (
    "LLM is not available. Please install llama-cpp-python and configure a model."
)
GENERATION_FAILED_MESSAGE = "Sorry, I'm having trouble generating a response right now."
UNEXPECTED_ERROR_MESSAGE = "Sorry, an unexpected error occurred. Please contact support."


def generate_answer(
    prompt: str,
    max_tokens: Optional[int] = None,
    fallback_provider=None,
) -> str:
    """
    Generates a completion from the language model for the given prompt.

    Args:
        prompt (str): The full prompt to send to the LLM.
        max_tokens (Optional[int]): Token generation limit, falling back to the config default.
        fallback_provider: Provider to use when no provider is currently selected.

    Returns:
        str: The model's generated text response, or a fallback message on failure.
    """
    provider = get_current_provider() or fallback_provider
    if provider is None:
        logger.warning(
            "LLM provider not available - returning fallback response")
        return PROVIDER_UNAVAILABLE_MESSAGE
    try:
        sanitized_prompt = sanitize_logs(prompt)
        return provider.generate(
            prompt=sanitized_prompt,
            max_tokens=max_tokens or llm_config["max_tokens"])
    except (ImportError, AttributeError) as e:
        logger.error("LLM provider unavailable: %s", e)
        return PROVIDER_UNAVAILABLE_MESSAGE
    except (ValueError, RuntimeError) as exc:
        logger.error("LLM generation failed: %s",
                     sanitize_log_payload(repr(exc)))
        logger.debug("Failed prompt payload: %s", sanitize_log_payload(prompt))
        return GENERATION_FAILED_MESSAGE
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(
            "Unexpected error during LLM generation: %s",
            sanitize_log_payload(repr(exc))
        )
        logger.debug("Failed prompt payload: %s", sanitize_log_payload(prompt))
        return UNEXPECTED_ERROR_MESSAGE


async def generate_answer_stream(
    prompt: str,
    max_tokens: Optional[int] = None,
    fallback_provider=None,
) -> AsyncGenerator[str, None]:
    """
    Generate streaming completion from LLM.

    Args:
        prompt (str): Full prompt for the model.
        max_tokens (Optional[int]): Token generation limit, falling back to the config default.
        fallback_provider: Provider to use when no provider is currently selected.

    Yields:
        str: Individual tokens.
    """
    provider = get_current_provider() or fallback_provider
    if provider is None:
        logger.warning(
            "LLM provider not available - returning fallback response")
        yield PROVIDER_UNAVAILABLE_MESSAGE
        return
    try:
        sanitized_prompt = sanitize_logs(prompt)
        async for token in provider.generate_stream(
            prompt=sanitized_prompt,
            max_tokens=max_tokens or llm_config["max_tokens"]
        ):
            yield token
    except (ImportError, AttributeError) as e:
        logger.error("LLM provider unavailable: %s", e)
        yield PROVIDER_UNAVAILABLE_MESSAGE
    except (ValueError, RuntimeError) as exc:
        logger.error("LLM streaming generation failed: %r", exc, exc_info=True)
        yield GENERATION_FAILED_MESSAGE
    except Exception:  # pylint: disable=broad-except
        logger.exception("Unexpected error during LLM streaming generation")
        yield UNEXPECTED_ERROR_MESSAGE
