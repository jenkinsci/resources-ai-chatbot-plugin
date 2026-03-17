"""Unit Tests for rag/embedding/bm25_indexer.py."""

import pytest
from rag.embedding.bm25_indexer import BM25Indexer


# =========================
# build() tests
# =========================
def test_build_stores_retriever_for_valid_config(mocker):
    """build() should store a retriever for each config when SparseRetriever is available."""
    mock_sr = mocker.Mock()
    mocker.patch("rag.embedding.bm25_indexer.SparseRetriever", mock_sr)

    indexer = _make_indexer(mocker)
    mock_indexed = mocker.Mock()
    mock_sr.return_value.index_file.return_value = mock_indexed

    indexer.build()

    assert "test_index" in indexer.retrievers
    assert indexer.retrievers["test_index"] == mock_indexed


def test_build_stores_multiple_retrievers(mocker):
    """build() should store retrievers for all valid configs."""
    mock_sr = mocker.Mock()
    mocker.patch("rag.embedding.bm25_indexer.SparseRetriever", mock_sr)

    configs = [
        {"index_name": "idx_a", "file_path": "a.jsonl"},
        {"index_name": "idx_b", "file_path": "b.jsonl"},
    ]
    indexer = BM25Indexer(index_configs=configs, logger=mocker.Mock())
    mock_sr.return_value.index_file.return_value = mocker.Mock()

    indexer.build()

    assert "idx_a" in indexer.retrievers
    assert "idx_b" in indexer.retrievers


def test_build_skips_config_when_sparse_retriever_unavailable(mocker):
    """build() should not populate retrievers when SparseRetriever is None."""
    mocker.patch("rag.embedding.bm25_indexer.SparseRetriever", None)

    indexer = _make_indexer(mocker)
    indexer.build()

    assert indexer.retrievers == {}


def test_build_skips_config_when_index_config_raises(mocker):
    """build() should skip a config whose _index_config returns None due to an error."""
    mock_sr = mocker.Mock()
    mocker.patch("rag.embedding.bm25_indexer.SparseRetriever", mock_sr)
    mock_sr.return_value.index_file.side_effect = RuntimeError("disk error")

    indexer = _make_indexer(mocker)
    indexer.build()

    assert indexer.retrievers == {}


# =========================
# _index_config() tests
# =========================
def test_index_config_returns_none_when_sparse_retriever_is_none(mocker):
    """_index_config() should return None immediately when SparseRetriever is None."""
    mocker.patch("rag.embedding.bm25_indexer.SparseRetriever", None)

    indexer = _make_indexer(mocker)
    result = indexer._index_config({"index_name": "idx", "file_path": "f.jsonl"})

    assert result is None


def test_index_config_returns_retriever_on_success(mocker):
    """_index_config() should return the indexed SparseRetriever on success."""
    mock_sr = mocker.Mock()
    mocker.patch("rag.embedding.bm25_indexer.SparseRetriever", mock_sr)
    mock_indexed = mocker.Mock()
    mock_sr.return_value.index_file.return_value = mock_indexed

    indexer = _make_indexer(mocker)
    result = indexer._index_config({"index_name": "idx", "file_path": "f.jsonl"})

    assert result == mock_indexed


def test_index_config_handles_indexing_error_gracefully(mocker):
    """_index_config() should catch exceptions, log the error, and return None."""
    mock_sr = mocker.Mock()
    mocker.patch("rag.embedding.bm25_indexer.SparseRetriever", mock_sr)
    mock_sr.return_value.index_file.side_effect = Exception("index failed")

    mock_logger = mocker.Mock()
    indexer = BM25Indexer(index_configs=[], logger=mock_logger)
    result = indexer._index_config({"index_name": "idx", "file_path": "f.jsonl"})

    assert result is None
    mock_logger.error.assert_called_once()
    assert "idx" in mock_logger.error.call_args[0][1]


# =========================
# get() tests
# =========================
def test_get_returns_cached_retriever(mocker):
    """get() should return the in-memory retriever without hitting disk."""
    mocker.patch("rag.embedding.bm25_indexer.SparseRetriever", mocker.Mock())

    indexer = _make_indexer(mocker)
    cached = mocker.Mock()
    indexer.retrievers["test_index"] = cached

    result = indexer.get("test_index")

    assert result is cached


def test_get_loads_retriever_from_disk_when_not_cached(mocker):
    """get() should load from disk and cache the result when not already in memory."""
    mock_sr = mocker.Mock()
    mocker.patch("rag.embedding.bm25_indexer.SparseRetriever", mock_sr)
    loaded = mocker.Mock()
    mock_sr.load.return_value = loaded

    indexer = _make_indexer(mocker)
    result = indexer.get("test_index")

    assert result is loaded
    assert indexer.retrievers["test_index"] is loaded
    mock_sr.load.assert_called_once_with("test_index")


def test_get_returns_none_when_load_fails(mocker):
    """get() should return None and log a warning when disk load raises an exception."""
    mock_sr = mocker.Mock()
    mocker.patch("rag.embedding.bm25_indexer.SparseRetriever", mock_sr)
    mock_sr.load.side_effect = Exception("not found")

    mock_logger = mocker.Mock()
    indexer = BM25Indexer(index_configs=[], logger=mock_logger)
    result = indexer.get("missing_index")

    assert result is None
    mock_logger.warning.assert_called_once()
    assert "missing_index" in mock_logger.warning.call_args[0][1]


def test_get_returns_none_when_sparse_retriever_unavailable(mocker):
    """get() should return None immediately when SparseRetriever is None."""
    mocker.patch("rag.embedding.bm25_indexer.SparseRetriever", None)

    indexer = _make_indexer(mocker)
    result = indexer.get("test_index")

    assert result is None


def test_get_does_not_call_load_when_retriever_cached(mocker):
    """get() should not call SparseRetriever.load when the retriever is already cached."""
    mock_sr = mocker.Mock()
    mocker.patch("rag.embedding.bm25_indexer.SparseRetriever", mock_sr)

    indexer = _make_indexer(mocker)
    indexer.retrievers["test_index"] = mocker.Mock()

    indexer.get("test_index")

    mock_sr.load.assert_not_called()


# =========================
# Helpers
# =========================
def _make_indexer(mocker):
    """Return a BM25Indexer with a single test config and a mock logger."""
    return BM25Indexer(
        index_configs=[{"index_name": "test_index", "file_path": "test.jsonl"}],
        logger=mocker.Mock(),
    )
