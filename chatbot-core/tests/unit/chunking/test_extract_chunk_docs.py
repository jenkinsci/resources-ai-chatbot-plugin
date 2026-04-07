"""Unit Tests for extract_chunk_docs module."""

from unittest.mock import Mock, patch
from data.chunking.extract_chunk_docs import (
    process_page,
    extract_chunks
)


@patch("data.chunking.extract_chunk_docs.build_chunk_dict")
@patch("data.chunking.extract_chunk_docs.assign_code_blocks_to_chunks")
@patch("data.chunking.extract_chunk_docs.extract_code_blocks")
@patch("data.chunking.extract_chunk_docs.extract_title")
def test_process_page_builds_chunks(
    mock_extract_title,
    mock_extract_code_blocks,
    mock_assign_chunks,
    mock_build_chunk_dict
):
    """Test it builds chunk dicts from content, and logs warning when no placeholders are found."""
    url = "http://example.com"
    html = "<html><body><h1>Title</h1><pre>code</pre></body></html>"
    text_splitter = Mock()
    text_splitter.split_text.return_value = ["chunk1", "chunk2"]

    mock_extract_title.return_value = "Mocked Title"
    mock_extract_code_blocks.return_value = ["code block"]
    mock_assign_chunks.return_value = [
        {"chunk_text": "chunk1", "code_blocks": ["code block"]}
    ]
    mock_build_chunk_dict.return_value = "chunk dict"

    # Patch logger to avoid real logging
    with patch("data.chunking.extract_chunk_docs.logger") as mock_logger:
        result = process_page(url, html, text_splitter)

        mock_extract_title.assert_called_once()
        mock_extract_code_blocks.assert_called_once()
        text_splitter.split_text.assert_called_once()
        mock_assign_chunks.assert_called_once()
        mock_build_chunk_dict.assert_called_once()
        assert result == ["chunk dict"]

        # Test warning logic when placeholder missing
        mock_extract_code_blocks.return_value = ["code block"]
        soup_text = "<html><body><pre>code</pre></body></html>"
        text_splitter.split_text.reset_mock()
        mock_assign_chunks.reset_mock()
        mock_build_chunk_dict.reset_mock()
        mock_logger.warning.reset_mock()

        process_page(url, soup_text, text_splitter)
        # Should log a warning because no placeholder
        mock_logger.warning.assert_called()


@patch("data.chunking.extract_chunk_docs.process_page")
@patch("data.chunking.extract_chunk_docs.get_text_splitter")
def test_extract_chunks_aggregates_chunks(mock_get_splitter, mock_process_page):
    """Test extract_chunks processes all docs and aggregates the chunks."""
    docs = {
        "http://a": "<html></html>",
        "http://b": "<html></html>"
    }

    mock_get_splitter.return_value = "splitter"
    mock_process_page.side_effect = [
        ["chunk A1", "chunk A2"],
        ["chunk B1"]
    ]

    result = extract_chunks(docs)

    mock_get_splitter.assert_called_once_with(500, 100)
    assert mock_process_page.call_count == 2
    assert result == ["chunk A1", "chunk A2", "chunk B1"]
