"""Unit Test for common chunking module."""
# pylint: disable=import-error

import json
import uuid
from unittest.mock import Mock, patch
from langchain.text_splitter import RecursiveCharacterTextSplitter
from data.chunking.chunking_utils import (
    save_chunks,
    read_json_file,
    build_chunk_dict,
    get_text_splitter
)


def test_save_chunks_writes_file(tmp_path):
    """Test save_chunks writes JSON file and logs info."""
    output_file = tmp_path / "output.json"
    data = [{"id": "1", "chunk_text": "Chuk text"}]
    logger = Mock()

    save_chunks(str(output_file), data, logger)

    assert len(list(tmp_path.iterdir())) == 1
    content = json.loads(output_file.read_text(encoding="utf-8"))
    assert content == data
    logger.info.assert_called_once()
    assert "Written" in logger.info.call_args[0][0]


@patch("builtins.open")
def test_save_chunks_handles_error(mock_open):
    """Test save_chunks logs error on OSError."""
    logger = Mock()
    fake_path = "/nonexistent/output.json"
    data = [{"id": "1", "chunk_text": "Test"}]
    mock_open.side_effect = OSError("Disk full")

    save_chunks(fake_path, data, logger)

    logger.error.assert_called_once()
    assert "File error while writing" in logger.error.call_args[0][0]


def test_read_json_file_returns_data(tmp_path):
    """Test read_json_file loads JSON data."""
    input_file = tmp_path / "input.json"
    test_data = {"key": "value"}
    input_file.write_text(json.dumps(test_data), encoding="utf-8")
    logger = Mock()

    result = read_json_file(str(input_file), logger)
    assert result == test_data
    logger.error.assert_not_called()


def test_read_json_file_handles_file_not_found(tmp_path):
    """Test read_json_file returns [] if file missing."""
    nonexistent_file = tmp_path / "missing.json"
    logger = Mock()

    result = read_json_file(str(nonexistent_file), logger)
    assert result == []
    logger.error.assert_called_once()
    assert "File error while reading" in logger.error.call_args[0][0]


def test_read_json_file_handles_json_decode_error(tmp_path):
    """Test read_json_file returns [] on JSON decode error."""
    input_file = tmp_path / "bad.json"
    input_file.write_text("{ invalid json }", encoding="utf-8")
    logger = Mock()

    result = read_json_file(str(input_file), logger)
    assert result == []
    logger.error.assert_called_once()
    assert "JSON decode error" in logger.error.call_args[0][0]


# pylint: disable=protected-access
def test_build_chunk_dict_generates_correct_structure():
    """Test build_chunk_dict returns valid chunk dict."""
    chunk_text = "some text"
    metadata = {"a": 1}
    code_blocks = ["code1"]

    chunk = build_chunk_dict(chunk_text, metadata, code_blocks)

    assert isinstance(chunk, dict)
    assert "id" in chunk
    uuid.UUID(chunk["id"])
    assert chunk["chunk_text"] == chunk_text
    assert chunk["metadata"] == metadata
    assert chunk["code_blocks"] == code_blocks


# pylint: disable=protected-access
def test_get_text_splitter_returns_splitter():
    """Test get_text_splitter returns configured splitter."""
    chunk_size = 100
    chunk_overlap = 10
    separators = ["\n", " "]

    splitter = get_text_splitter(chunk_size, chunk_overlap, separators)

    assert isinstance(splitter, RecursiveCharacterTextSplitter)
    assert splitter._chunk_size == chunk_size
    assert splitter._chunk_overlap == chunk_overlap
    assert splitter._separators == separators


def test_get_text_splitter_defaults_separators():
    """Test get_text_splitter uses default separators."""
    splitter = get_text_splitter(100, 10)

    assert isinstance(splitter, RecursiveCharacterTextSplitter)
    assert splitter._separators == ["\n\n", "\n", " ", ""]
