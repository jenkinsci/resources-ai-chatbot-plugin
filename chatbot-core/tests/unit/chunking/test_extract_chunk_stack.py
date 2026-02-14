"""Unit Tests for extract_chunk_stack module."""
# pylint: disable=import-error, redefined-outer-name

from unittest.mock import Mock, patch
import pytest
from data.chunking.extract_chunk_stack import StackOverflowChunker

@pytest.fixture
def stack_overflow_chunker():
    """Returns a StackOverflowChunker instance."""
    return StackOverflowChunker()

@patch("data.chunking.extract_chunk_stack.build_chunk_dict")
@patch("data.chunking.extract_chunk_stack.assign_code_blocks_to_chunks")
@patch("data.chunking.extract_chunk_stack.extract_code_blocks")
def test_process_thread_returns_chunks(
    mock_extract_code,
    mock_assign_blocks,
    mock_build_chunk,
    stack_overflow_chunker
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
    stack_overflow_chunker.text_splitter = Mock()
    stack_overflow_chunker.text_splitter.split_text.return_value = ["chunk1"]
    mock_extract_code.return_value = ["code block"]
    mock_assign_blocks.return_value = [
        {"chunk_text": "chunk", "code_blocks": ["code block"]}
    ]
    mock_build_chunk.return_value = "chunk dict"

    result = stack_overflow_chunker.process_thread(thread)

    mock_extract_code.assert_called_once()
    stack_overflow_chunker.text_splitter.split_text.assert_called_once()
    mock_assign_blocks.assert_called_once()
    mock_build_chunk.assert_called_once()
    assert result == ["chunk dict"]


def test_process_thread_missing_content_returns_empty(stack_overflow_chunker):
    """Test process_thread returns empty if content missing."""
    thread = {
        "Question ID": 456,
        "Question Body": "",
        "Answer Body": ""
    }
    stack_overflow_chunker.logger = Mock()
    result = stack_overflow_chunker.process_thread(thread)

    assert result == []
    stack_overflow_chunker.logger.warning.assert_called_once()
    assert "missing question/answer content" in stack_overflow_chunker.logger.warning.call_args[0][0]


@patch("data.chunking.extract_chunk_stack.StackOverflowChunker.process_thread")
def test_extract_chunks_aggregates_chunks(
    mock_process_thread, stack_overflow_chunker
):
    """Test extract_chunks aggregates all chunks."""
    threads = [
        {"Question ID": 1},
        {"Question ID": 2}
    ]

    mock_process_thread.side_effect = [
        ["chunk1a", "chunk1b"],
        ["chunk2a"]
    ]

    result = stack_overflow_chunker.extract_chunks(threads)

    assert mock_process_thread.call_count == 2
    assert result == ["chunk1a", "chunk1b", "chunk2a"]
