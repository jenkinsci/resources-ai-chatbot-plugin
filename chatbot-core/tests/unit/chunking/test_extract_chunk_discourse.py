"""Unit Tests for extact_chunk_discourse module."""

from unittest.mock import Mock, patch
from data.chunking.extract_chunk_discourse import (
    extract_code_blocks,
    process_thread,
    extract_chunks
)

def test_extract_code_blocks_triple_backtick():
    """Test extracting triple-backtick code blocks."""
    text = "Some intro.\n```python\nprint('hello')\n```\nMore text."
    code_blocks, clean_text = extract_code_blocks(text)
    assert code_blocks == ["print('hello')"]
    assert "[[CODE_BLOCK_0]]" in clean_text


def test_extract_code_blocks_inline_backtick():
    """Test extracting inline backtick code snippets."""
    text = "Some text with `inline code` example."
    code_blocks, clean_text = extract_code_blocks(text)
    assert code_blocks == ["inline code"]
    assert "[[CODE_SNIPPET_0]]" in clean_text


def test_extract_code_blocks_mixed():
    """Test extracting mixed triple and inline code blocks."""
    text = "Before.\n```sql\nSELECT *\n```\nAnd `inline`."
    code_blocks, clean_text = extract_code_blocks(text)
    assert code_blocks == ["SELECT *", "inline"]
    assert "[[CODE_BLOCK_0]]" in clean_text
    assert "[[CODE_SNIPPET_1]]" in clean_text


def test_extract_code_blocks_no_code():
    """Test extracting when no code is present."""
    text = "Just some plain text without code."
    code_blocks, clean_text = extract_code_blocks(text)
    assert not code_blocks
    assert clean_text == text


@patch("data.chunking.extract_chunk_discourse.build_chunk_dict")
@patch("data.chunking.extract_chunk_discourse.assign_code_blocks_to_chunks")
def test_process_thread_returns_chunks(mock_assign, mock_build):
    """Test process_thread builds chunk dicts correctly."""
    thread = {
        "topic_id": 42,
        "title": "Test Title",
        "posts": ["Post 1 text.", "Post 2 text."]
    }
    mock_text_splitter = Mock()
    mock_text_splitter.split_text.return_value = ["chunk1", "chunk2"]

    mock_assign.return_value = [
        {"chunk_text": "chunk1", "code_blocks": ["c1"]},
        {"chunk_text": "chunk2", "code_blocks": ["c2"]}
    ]

    mock_build.side_effect = ["chunkdict1", "chunkdict2"]

    result = process_thread(thread, mock_text_splitter)

    mock_text_splitter.split_text.assert_called_once()
    mock_assign.assert_called_once()
    assert mock_build.call_count == 2
    assert result == ["chunkdict1", "chunkdict2"]


@patch("data.chunking.extract_chunk_discourse.get_text_splitter")
@patch("data.chunking.extract_chunk_discourse.process_thread")
def test_extract_chunks_aggregates_all_chunks(mock_process, mock_splitter):
    """Test extract_chunks processes and combines all threads."""
    threads = [
        {"topic_id": 1},
        {"topic_id": 2}
    ]

    mock_splitter.return_value = "splitter"
    mock_process.side_effect = [
        ["chunk1a", "chunk1b"],
        ["chunk2a"]
    ]

    result = extract_chunks(threads)
    mock_splitter.assert_called_once_with(500, 100)
    assert mock_process.call_count == 2
    assert result == ["chunk1a", "chunk1b", "chunk2a"]
