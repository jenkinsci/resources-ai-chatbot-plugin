"""Unit Tests for retrieve_utils module."""

import numpy as np
import pytest
from rag.retriever.retriever_utils import load_vector_index, search_index, INDEX_PATH, METADATA_PATH

def test_load_vector_index_returns_index_and_metadata(mocker):
    """Test load_vector_index loads index and metadata correctly."""
    mock_logger = mocker.Mock()
    mock_index = mocker.Mock()
    mock_metadata = [{"id": 1}]
    mock_load_index = mocker.patch(
        "rag.retriever.retriever_utils.load_faiss_index",
        return_value=mock_index
    )
    mock_load_metadata = mocker.patch(
        "rag.retriever.retriever_utils.load_metadata",
        return_value=mock_metadata
    )

    index, metadata = load_vector_index(mock_logger)

    mock_load_index.assert_called_once_with(INDEX_PATH, mock_logger)
    mock_load_metadata.assert_called_once_with(METADATA_PATH, mock_logger)
    assert index == mock_index
    assert metadata == mock_metadata


def test_search_index_invalid_query_vector(mocker):
    """Test search_index returns empty if query vector is invalid."""
    mock_logger = mocker.Mock()
    index = mocker.Mock()
    metadata = [{"id": 1}]
    data, scores = search_index(
        query_vector=None,
        index=index,
        metadata=metadata,
        logger=mock_logger,
        top_k=5
    )
    mock_logger.error.assert_called_once_with("Invalid query vector received.")
    assert not data
    assert not scores


def test_search_index_empty_index(mocker):
    """Test search_index returns empty if index has no vectors."""
    mock_logger = mocker.Mock()
    index = mocker.Mock()
    index.ntotal = 0
    metadata = [{"id": 1}]
    query_vector = np.array([0.1, 0.2], dtype=np.float32)
    data, scores = search_index(
        query_vector=query_vector,
        index=index,
        metadata=metadata,
        logger=mock_logger,
        top_k=3
    )
    mock_logger.warning.assert_called_once_with(
        "FAISS index is empty. No search will be performed."
    )
    assert not data
    assert not scores


def test_search_index_successful(mocker):
    """Test search_index returns top-k results correctly."""
    mock_logger = mocker.Mock()
    index = mocker.Mock()
    index.ntotal = 2
    index.search.return_value = (
        np.array([[0.01, 0.02]], dtype=np.float32),
        np.array([[0, 1]])
    )
    metadata = [{"id": "doc1"}, {"id": "doc2"}]
    query_vector = np.array([0.1, 0.2], dtype=np.float32)

    data, scores = search_index(
        query_vector=query_vector,
        index=index,
        metadata=metadata,
        logger=mock_logger,
        top_k=2
    )

    index.search.assert_called_once()
    assert data == [{"id": "doc1"}, {"id": "doc2"}]
    assert scores == pytest.approx([0.01, 0.02])


def test_search_index_out_of_bounds_index(mocker):
    """Test search_index logs error if FAISS returns invalid index."""
    mock_logger = mocker.Mock()
    index = mocker.Mock()
    index.ntotal = 2
    index.search.return_value = (
        np.array([[0.1, 0.2]]),
        np.array([[0, 5]])
    )
    metadata = [{"id": "doc1"}]
    query_vector = np.array([0.1, 0.2], dtype=np.float32)

    data, scores = search_index(
        query_vector=query_vector,
        index=index,
        metadata=metadata,
        logger=mock_logger,
        top_k=2
    )

    mock_logger.error.assert_called_once()
    assert "out of range" in mock_logger.error.call_args[0][0]
    assert data == [{"id": "doc1"}]
    assert scores == pytest.approx([0.1])


def test_search_index_warns_when_metadata_longer_than_index(mocker):
    """Test search_index warns if metadata has more entries than index.ntotal."""
    mock_logger = mocker.Mock()
    index = mocker.Mock()
    index.ntotal = 1
    index.search.return_value = (
        np.array([[0.1]]),
        np.array([[0]])
    )
    metadata = [{"id": "doc1"}, {"id": "extra_doc"}]
    query_vector = np.array([0.1, 0.2], dtype=np.float32)

    data, scores = search_index(
        query_vector=query_vector,
        index=index,
        metadata=metadata,
        logger=mock_logger,
        top_k=1
    )

    mock_logger.warning.assert_any_call(
        "Index contains %d vectors but metadata has %d entries." \
        " Some results may be missing or inconsistent.",
        1,
        2
    )

    mock_logger.error.assert_not_called()
    assert data == [{"id": "doc1"}]
    assert scores == pytest.approx([0.1])
