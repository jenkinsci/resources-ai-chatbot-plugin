"""
Runtime lazy model loader with caching and error handling.

This module provides thread-safe, lazy initialization for heavy components
(embedding model and LLM provider) that should not be loaded at import time.
Models are initialized on first use and cached for subsequent calls.
"""

from threading import Lock
from typing import Optional, Dict, Any
from utils import LoggerFactory

logger = LoggerFactory.instance().get_logger("models")

# Caching and locking for lazy initialization
_models_cache: Dict[str, Any] = {}
_models_lock = Lock()
_models_errors: Dict[str, str] = {}


def get_embedding_model():
    """
    Lazily load and cache the sentence transformer embedding model.
    
    Returns:
        Optional[SentenceTransformer]: The loaded model, or None if initialization failed.
                                       Check logs for error details.
    """
    return _get_cached_model(
        "embedding",
        _load_embedding_model_impl
    )


def get_llm_provider():
    """
    Lazily load and cache the LLM provider.
    
    Returns:
        Optional[LlamaCppProvider]: The loaded provider, or None if initialization failed.
                                    Check logs for error details.
    """

    return _get_cached_model(
        "llm",
        _load_llm_provider_impl
    )


def get_models_status() -> Dict[str, Any]:
    """
    Get the current status of all cached models (for health checks).
    
    Returns:
        dict: Status object with keys:
              - embedding_available: bool
              - llm_available: bool
              - embedding_error: Optional[str]
              - llm_error: Optional[str]
    """
    return {
        "embedding_available": "embedding" in _models_cache,
        "llm_available": "llm" in _models_cache,
        "embedding_error": _models_errors.get("embedding"),
        "llm_error": _models_errors.get("llm"),
    }


def _get_cached_model(model_name: str, loader_fn) -> Optional[Any]:
    """
    Generic lazy loader with caching and thread-safe locking.
    
    Args:
        model_name: Key for caching (e.g., "embedding", "llm")
        loader_fn: Callable that returns the loaded model or raises an exception
    
    Returns:
        The cached model instance, or None if initialization failed.
    """
    if model_name in _models_cache:
        logger.debug(f"{model_name} model already cached, returning existing instance")
        return _models_cache[model_name]
    
    if model_name in _models_errors:
        return None
    
    with _models_lock:
        # Double-check after acquiring lock
        if model_name in _models_cache:
            return _models_cache[model_name]
        if model_name in _models_errors:
            return None
        
        try:
            logger.info(f"Initializing {model_name} model for the first time...")
            model = loader_fn()
            _models_cache[model_name] = model
            logger.info(f"{model_name} model initialized successfully")
            return model
        except Exception as exc:
            error_msg = f"Failed to initialize {model_name}: {type(exc).__name__}: {exc}"
            _models_errors[model_name] = error_msg
            logger.error(error_msg, exc_info=True)
            return None


def _load_embedding_model_impl():
    """
    Internal: actually load the embedding model.
    Called only on first use and under lock.
    """
    from sentence_transformers import SentenceTransformer
    from api.config.loader import CONFIG
    
    model_name = CONFIG["retrieval"]["embedding_model_name"]
    logger.debug(f"Loading embedding model: {model_name}")
    return SentenceTransformer(model_name)


def _load_llm_provider_impl():
    """
    Internal: actually load the LLM provider.
    Called only on first use and under lock.
    """
    from api.models.llama_cpp_provider import LlamaCppProvider
    from api.config.loader import CONFIG
    
    if CONFIG.get("is_test_mode", False):
        logger.info("Test mode enabled: LLM provider will not be instantiated")
        return None
    
    logger.debug("Initializing LLM provider...")
    return LlamaCppProvider()

