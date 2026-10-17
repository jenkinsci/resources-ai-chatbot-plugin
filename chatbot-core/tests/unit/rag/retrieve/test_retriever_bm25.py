"""Unit tests for BM25 keyword search, ranking, and index lookup."""

import pytest

from rag.retriever.retriever_bm25 import (
    perform_keyword_search,
    perform_keyword_search_from_source,
    search_bm25_index,
)


def _metadata(*chunk_ids):
    """Build metadata rows whose ids the keyword search can join."""
    return [{"id": chunk_id, "chunk_text": f"text for {chunk_id}"} for chunk_id in chunk_ids]


def test_perform_keyword_search_rejects_empty_query(mocker):
    """Blank queries are logged and never sent to the sparse index."""
    logger = mocker.Mock()
    index = mocker.Mock()

    assert perform_keyword_search("   ", logger, index, _metadata("a"), 0.1) == []

    logger.warning.assert_called_once_with("Empty query received.")
    index.search.assert_not_called()


def test_search_bm25_index_preserves_retriever_ranking(mocker):
    """Hits stay in the order returned by the sparse retriever, not metadata order."""
    logger = mocker.Mock()
    index = mocker.Mock()
    metadata = _metadata("low", "high")
    index.search.return_value = [
        {"id": "high", "score": 2.4},
        {"id": "low", "score": 0.2},
    ]

    data, scores = search_bm25_index("jenkins agent", index, metadata, logger, top_k=2)

    index.search.assert_called_once_with(
        query="jenkins agent",
        return_docs=True,
        cutoff=2,
    )
    assert [item["id"] for item in data] == ["high", "low"]
    assert scores == [2.4, 0.2]
    logger.warning.assert_not_called()


def test_perform_keyword_search_filters_below_threshold_and_keeps_rank(mocker):
    """Scores under the threshold drop out without reordering the hits that remain."""
    logger = mocker.Mock()
    index = mocker.Mock()
    index.search.return_value = [
        {"id": "a", "score": 1.5},
        {"id": "b", "score": 0.4},
        {"id": "c", "score": 0.5},
    ]

    results = perform_keyword_search(
        "pipeline",
        logger,
        index,
        _metadata("a", "b", "c"),
        keyword_threshold=0.5,
        top_k=3,
    )

    assert [item["chunk"]["id"] for item in results] == ["a", "c"]
    assert [item["score"] for item in results] == [1.5, 0.5]


def test_search_bm25_index_warns_when_metadata_is_missing(mocker):
    """A hit whose id is absent from metadata is skipped and logged."""
    logger = mocker.Mock()
    index = mocker.Mock()
    kept = {"id": "kept", "chunk_text": "text for kept"}
    index.search.return_value = [
        {"id": "gone", "score": 1.0},
        {"id": "kept", "score": 0.5},
    ]

    data, _scores = search_bm25_index("query", index, [kept], logger, top_k=2)

    assert data == [kept]
    logger.warning.assert_called_once_with(
        "No metadata found for chunk ID: %s",
        "gone",
    )


@pytest.mark.parametrize(
    ("index_found", "metadata"),
    [
        (False, [{"id": "a"}]),
        (True, None),
        (True, []),
    ],
)
def test_keyword_search_from_source_returns_empty_without_index_or_metadata(
    mocker, index_found, metadata
):
    """Source search stops when the BM25 index or its metadata cannot be loaded."""
    logger = mocker.Mock()
    index = mocker.Mock() if index_found else None
    mocker.patch("rag.retriever.retriever_bm25.indexer.get", return_value=index)
    mocker.patch(
        "rag.retriever.retriever_bm25.load_vector_index",
        return_value=(index, metadata),
    )

    results = perform_keyword_search_from_source("jenkins", logger, "plugins", 0.2)

    assert results == []
    if index is not None:
        index.search.assert_not_called()


def test_keyword_search_from_source_ranks_and_filters(mocker):
    """Source search loads the named index and returns thresholded ranked chunks."""
    logger = mocker.Mock()
    index = mocker.Mock()
    metadata = _metadata("high", "low")
    index.search.return_value = [
        {"id": "high", "score": 3.0},
        {"id": "low", "score": 0.1},
    ]
    mock_get = mocker.patch(
        "rag.retriever.retriever_bm25.indexer.get",
        return_value=index,
    )
    mock_load = mocker.patch(
        "rag.retriever.retriever_bm25.load_vector_index",
        return_value=(index, metadata),
    )

    results = perform_keyword_search_from_source(
        "jenkins agent",
        logger,
        "plugins",
        keyword_threshold=1.0,
        top_k=4,
    )

    mock_get.assert_called_once_with("plugins")
    mock_load.assert_called_once_with(logger, "plugins")
    index.search.assert_called_once_with(
        query="jenkins agent",
        return_docs=True,
        cutoff=4,
    )
    assert results == [{"chunk": metadata[0], "score": 3.0}]
