"""Unit Tests for retrieve module."""

from rag.retriever import retrieve

def test_get_relevant_documents_empty_query(mocker):
    """Test that empty query returns empty results."""
    mock_logger = mocker.Mock()
    model = mocker.Mock()

    data, scores = retrieve.get_relevant_documents(
        query="   ",
        model=model,
        logger=mock_logger,
        top_k=3
    )

    mock_logger.warning.assert_called_once_with("Empty query received.")
    assert not data
    assert not scores


def test_get_relevant_documents_no_index(mocker):
    """Test that missing index returns empty results."""
    mock_logger = mocker.Mock()
    model = mocker.Mock()

    mocker.patch(
        "rag.retriever.retrieve.load_vector_index",
        return_value=(None, [{"id": 1}])
    )

    data, scores = retrieve.get_relevant_documents(
        query="some valid query",
        model=model,
        logger=mock_logger,
        top_k=3
    )

    assert not data
    assert not scores


def test_get_relevant_documents_no_metadata(mocker):
    """Test that missing metadata returns empty."""
    mock_logger = mocker.Mock()
    model = mocker.Mock()

    mocker.patch(
        "rag.retriever.retrieve.load_vector_index",
        return_value=(mocker.Mock(), None)
    )

    data, scores = retrieve.get_relevant_documents(
        query="some valid query",
        model=model,
        logger=mock_logger,
        top_k=3
    )

    assert not data
    assert not scores


def test_get_relevant_documents_success(mocker):
    """Test successful retrieval pipeline."""
    mock_logger = mocker.Mock()
    model = mocker.Mock()

    mock_index = mocker.Mock()
    mock_metadata = [{"id": "doc1"}]
    mocker.patch(
        "rag.retriever.retrieve.load_vector_index",
        return_value=(mock_index, mock_metadata)
    )

    mock_embed_documents = mocker.patch(
        "rag.retriever.retrieve.embed_documents",
        return_value=[[0.1, 0.2]]
    )

    mock_search_index = mocker.patch(
        "rag.retriever.retrieve.search_index",
        return_value=([{"id": "doc1"}], [0.99])
    )

    query = "some valid query"

    data, scores = retrieve.get_relevant_documents(
        query=query,
        model=model,
        logger=mock_logger,
        top_k=1
    )

    mock_embed_documents.assert_called_once_with([query], model, mock_logger)
    mock_search_index.assert_called_once_with(
        [0.1, 0.2],
        mock_index,
        mock_metadata,
        mock_logger,
        1
    )

    assert data == [{"id": "doc1"}]
    assert scores == [0.99]
