"""Lazy loading utilities for the sentence-transformer embedding model."""

from threading import Lock

from rag.embedding.embedding_utils import load_embedding_model
from api.config.loader import CONFIG
from utils import LoggerFactory

logger = LoggerFactory.instance().get_logger("api")
_MODEL_STATE = {
    "model": None,
    "initialized": False,
}
_MODEL_LOCK = Lock()


def get_embedding_model():
    """
    Lazily initialize and cache the embedding model.

    Returns:
        SentenceTransformer | None: Loaded model instance, or None if loading failed.
    """
    if _MODEL_STATE["initialized"]:
        return _MODEL_STATE["model"]

    with _MODEL_LOCK:
        if _MODEL_STATE["initialized"]:
            return _MODEL_STATE["model"]

        try:
            _MODEL_STATE["model"] = load_embedding_model(
                CONFIG["retrieval"]["embedding_model_name"], logger
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error(
                "Embedding model initialization failed: %s",
                exc,
                exc_info=True,
            )
            _MODEL_STATE["model"] = None
        finally:
            _MODEL_STATE["initialized"] = True

    return _MODEL_STATE["model"]


def reset_embedding_model_cache() -> None:
    """Reset model cache. Used in unit tests."""
    with _MODEL_LOCK:
        _MODEL_STATE["model"] = None
        _MODEL_STATE["initialized"] = False
