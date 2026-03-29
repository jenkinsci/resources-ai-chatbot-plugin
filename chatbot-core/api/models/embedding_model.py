"""
Embedding model lazy loader wrapper.

This module provides access to the sentence transformer embedding model
through lazy initialization to avoid blocking startup with heavy model loads.

DEPRECATED: Direct access to EMBEDDING_MODEL global is no longer supported.
Use api.models.runtime_models.get_embedding_model() instead.
"""

from api.models.runtime_models import get_embedding_model

# For backward compatibility during transition, provide a lazy property-like accessor
# but warn about the deprecated approach
def _get_embedding_model_compat():
    """Backward compatibility wrapper."""
    model = get_embedding_model()
    if model is None:
        raise RuntimeError(
            "Embedding model not available. "
            "Check logs for initialization errors. "
            "Consider using get_embedding_model() for graceful degraded mode."
        )
    return model

# Module-level getter for compatibility, but do NOT eagerly load
EMBEDDING_MODEL = property(lambda self: _get_embedding_model_compat())
