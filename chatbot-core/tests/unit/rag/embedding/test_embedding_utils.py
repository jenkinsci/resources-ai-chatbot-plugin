"""Unit Tests for Embedding Utils."""

import pytest
from rag.embedding.embedding_utils import load_embedding_model, embed_documents

def test_load_embedding_model_logs_loading_message(mock_sentence_transformer, mocker):
    """Testing that load_embedding_model logs when loading model."""
    model_name = "embedding-model-name"
    mock_sentence_transformer.return_value = mocker.Mock()
    mock_logger = mocker.Mock()

    model = load_embedding_model(model_name, mock_logger)

    assert model is not None
    assert model == mock_sentence_transformer.return_value
    mock_logger.info.assert_called_once_with(f"Loading embedding model: {model_name}")

def test_embed_documents_success(mock_model_encode, mocker):
    """Testing that embed_documents calls model.encode and returns embeddings."""
    mock_model_encode.encode.return_value = ["embedding1", "embedding2"]
    mock_logger = mocker.Mock()

    texts = ["chunk1", "chunk2"]

    result = embed_documents(texts, mock_model_encode, mock_logger, batch_size=16)

    assert result == ["embedding1", "embedding2"]
    mock_model_encode.encode.assert_called_once_with(
        texts,
        batch_size=16,
        show_progress_bar=True
    )
    mock_logger.info.assert_called_once_with("Embedding 2 documents")

def test_embed_documents_raises_typeerror_on_invalid_model(mocker):
    """Testing that embed_documents raises TypeError if model type is invalid."""
    invalid_model = "I am not a model instance"

    with pytest.raises(TypeError, match="Model must be a SentenceTransformer instance."):
        embed_documents(["chunk1"], model=invalid_model, logger=mocker.Mock())
