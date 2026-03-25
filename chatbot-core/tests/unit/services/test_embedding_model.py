"""Unit tests for lazy embedding model initialization."""

import importlib


def test_embedding_model_not_loaded_on_module_import(mocker):
    """Importing embedding_model must not eagerly load the heavy model."""
    mocked_loader = mocker.patch(
        "rag.embedding.embedding_utils.load_embedding_model"
    )
    from api.models import embedding_model  # pylint: disable=import-outside-toplevel
    importlib.reload(embedding_model)

    assert mocked_loader.call_count == 0


def test_get_embedding_model_loads_once_and_caches(mocker):
    """get_embedding_model should initialize once and return the cached instance."""
    mocked_loader = mocker.patch(
        "rag.embedding.embedding_utils.load_embedding_model",
        return_value="mock-model",
    )
    from api.models import embedding_model  # pylint: disable=import-outside-toplevel
    importlib.reload(embedding_model)

    first = embedding_model.get_embedding_model()
    second = embedding_model.get_embedding_model()

    assert first == "mock-model"
    assert second == "mock-model"
    mocked_loader.assert_called_once()


def test_get_embedding_model_failed_init_returns_none_without_retries(mocker):
    """Failed initialization should return None and avoid repeated re-initialization."""
    mocked_loader = mocker.patch(
        "rag.embedding.embedding_utils.load_embedding_model",
        side_effect=RuntimeError("model unavailable"),
    )
    from api.models import embedding_model  # pylint: disable=import-outside-toplevel
    importlib.reload(embedding_model)

    first = embedding_model.get_embedding_model()
    second = embedding_model.get_embedding_model()

    assert first is None
    assert second is None
    mocked_loader.assert_called_once()
