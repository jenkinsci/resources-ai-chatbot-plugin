"""Unit Tests for extract_chunk_docs module."""
# pylint: disable=import-error, redefined-outer-name, unused-argument

from unittest.mock import Mock, patch
import pytest
from data.chunking.extract_chunk_docs import DocsChunker

@pytest.fixture
def docs_chunker():
    """Returns a DocsChunker instance."""
    return DocsChunker()

@patch("data.chunking.extract_chunk_docs.build_chunk_dict")
@patch("data.chunking.extract_chunk_docs.assign_code_blocks_to_chunks")
@patch("data.chunking.extract_chunk_docs.extract_code_blocks")
@patch("data.chunking.extract_chunk_docs.extract_title")
def test_process_page_builds_chunks(
    mock_extract_title,
    mock_extract_code_blocks,
    mock_assign_chunks,
    mock_build_chunk_dict,
    docs_chunker
):
    """Test that process_page correctly builds chunk dictionaries from page content."""
    url = "http://example.com"
    html = "<html><body><h1>Title</h1><pre>code</pre></body></html>"
    docs_chunker.text_splitter = Mock()
    docs_chunker.text_splitter.split_text.return_value = ["chunk1", "chunk2"]

    mock_extract_title.return_value = "Mocked Title"
    mock_extract_code_blocks.return_value = ["code block"]
    mock_assign_chunks.return_value = [
        {"chunk_text": "chunk1", "code_blocks": ["code block"]}
    ]
    mock_build_chunk_dict.return_value = "chunk dict"

    result = docs_chunker.process_page(url, html)

    mock_extract_title.assert_called_once()
    mock_extract_code_blocks.assert_called_once()
    docs_chunker.text_splitter.split_text.assert_called_once()
    mock_assign_chunks.assert_called_once()
    mock_build_chunk_dict.assert_called_once()
    assert result == ["chunk dict"]


@patch("data.chunking.extract_chunk_docs.assign_code_blocks_to_chunks", return_value=[])
@patch("data.chunking.extract_chunk_docs.extract_code_blocks")
def test_process_page_logs_warning_on_missing_placeholder(
    mock_extract_code_blocks,
    _mock_assign_chunks,
    docs_chunker
):
    """Test process_page logs a warning if code is found but no placeholder is in the text."""
    url = "http://example.com"
    html_with_code = "<html><body><pre>code</pre></body></html>"
    docs_chunker.text_splitter = Mock()
    docs_chunker.text_splitter.split_text.return_value = ["chunk without placeholder"]
    docs_chunker.logger = Mock()
    mock_extract_code_blocks.return_value = ["some code"]

    docs_chunker.process_page(url, html_with_code)

    docs_chunker.logger.warning.assert_called_once()
    assert "no placeholders found" in docs_chunker.logger.warning.call_args[0][0]


@patch("data.chunking.extract_chunk_docs.DocsChunker.process_page")
def test_extract_chunks_aggregates_chunks(mock_process_page, docs_chunker):
    """Test extract_chunks processes all docs and aggregates the chunks."""
    docs = {
        "http://a": "<html></html>",
        "http://b": "<html></html>"
    }

    mock_process_page.side_effect = [
        ["chunk A1", "chunk A2"],
        ["chunk B1"]
    ]

    result = docs_chunker.extract_chunks(docs)

    assert mock_process_page.call_count == 2
    assert result == ["chunk A1", "chunk A2", "chunk B1"]
