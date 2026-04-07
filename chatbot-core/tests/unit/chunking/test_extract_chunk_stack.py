"""Unit Tests for extract_chunk_stack module."""

from unittest.mock import Mock, patch
from bs4 import BeautifulSoup
from data.chunking.extract_chunk_stack import (
    clean_html,
    process_thread,
    extract_chunks
)


def test_clean_html_parses_html():
    """Test clean_html returns parsed BeautifulSoup."""
    html = "<div><p>Hello</p></div>"
    soup = clean_html(html)
    assert isinstance(soup, BeautifulSoup)
    assert soup.find("p").text == "Hello"


@patch("data.chunking.extract_chunk_stack.build_chunk_dict")
@patch("data.chunking.extract_chunk_stack.assign_code_blocks_to_chunks")
@patch("data.chunking.extract_chunk_stack.extract_code_blocks")
def test_process_thread_returns_chunks(
    mock_extract_code,
    mock_assign_blocks,
    mock_build_chunk
):
    """Test process_thread builds chunk dicts."""
    thread = {
        "Question ID": 123,
        "Question Body": "<p>Q body</p>",
        "Answer Body": "<pre>code</pre>",
        "Question Title": "Sample Question",
        "Tags": "python",
        "CreationDate": "2024-01-01",
        "Question Score": 5,
        "Answer Score": 10
    }
    text_splitter = Mock()
    text_splitter.split_text.return_value = ["chunk1"]
    mock_extract_code.return_value = ["code block"]
    mock_assign_blocks.return_value = [
        {"chunk_text": "chunk", "code_blocks": ["code block"]}
    ]
    mock_build_chunk.return_value = "chunk dict"

    result = process_thread(thread, text_splitter)

    mock_extract_code.assert_called_once()
    text_splitter.split_text.assert_called_once()
    mock_assign_blocks.assert_called_once()
    mock_build_chunk.assert_called_once()
    assert result == ["chunk dict"]


@patch("data.chunking.extract_chunk_stack.logger")
def test_process_thread_missing_content_returns_empty(mock_logger):
    """Test process_thread returns empty if content missing."""
    thread = {
        "Question ID": 456,
        "Question Body": "",
        "Answer Body": ""
    }
    text_splitter = Mock()
    result = process_thread(thread, text_splitter)

    assert result == []
    mock_logger.warning.assert_called_once()
    assert "missing question/answer content" in mock_logger.warning.call_args[0][0]


@patch("data.chunking.extract_chunk_stack.process_thread")
@patch("data.chunking.extract_chunk_stack.get_text_splitter")
def test_extract_chunks_aggregates_chunks(mock_get_splitter, mock_process_thread):
    """Test extract_chunks aggregates all chunks."""
    threads = [
        {"Question ID": 1},
        {"Question ID": 2}
    ]

    mock_get_splitter.return_value = "splitter"
    mock_process_thread.side_effect = [
        ["chunk1a", "chunk1b"],
        ["chunk2a"]
    ]

    result = extract_chunks(threads)

    mock_get_splitter.assert_called_once_with(500, 100)
    assert mock_process_thread.call_count == 2
    assert result == ["chunk1a", "chunk1b", "chunk2a"]
