"""Unit Tests for extract_chunk_plugins module."""

from unittest.mock import patch
from data.chunking.extract_chunk_plugins import (
    process_plugin,
    extract_chunks
)

@patch("data.chunking.extract_chunk_plugins.build_chunk_dict")
@patch("data.chunking.extract_chunk_plugins.assign_code_blocks_to_chunks")
@patch("data.chunking.extract_chunk_plugins.extract_code_blocks")
def test_process_plugin_returns_chunks(
    mock_extract_code,
    mock_assign_chunks,
    mock_build_chunk,
    mocker
):
    """Test that it extracts code blocks, splits text,assigns code blocks to chunks."""
    plugin_name = "Test Plugin"
    html = "<html><body><pre>code</pre></body></html>"
    text_splitter = mocker.Mock()
    text_splitter.split_text.return_value = ["chunk1"]

    mock_extract_code.return_value = ["code block"]
    mock_assign_chunks.return_value = [
        {"chunk_text": "chunk1", "code_blocks": ["code block"]}
    ]
    mock_build_chunk.return_value = "chunk dict"

    result = process_plugin(plugin_name, html, text_splitter)

    mock_extract_code.assert_called_once()
    text_splitter.split_text.assert_called_once()
    mock_assign_chunks.assert_called_once()
    mock_build_chunk.assert_called_once()
    assert result == ["chunk dict"]


@patch("data.chunking.extract_chunk_plugins.logger")
@patch("data.chunking.extract_chunk_plugins.extract_code_blocks")
def test_process_plugin_logs_warning_when_no_placeholder(
    mock_extract_code,
    mock_logger,
    mocker
):
    """Test process_plugin logs warning if no placeholders."""
    plugin_name = "PluginX"
    html = "<html><body><pre>some code</pre></body></html>"
    text_splitter = mocker.Mock()
    text_splitter.split_text.return_value = ["chunk1"]

    mock_extract_code.return_value = ["code block"]

    with patch("data.chunking.extract_chunk_plugins.assign_code_blocks_to_chunks") as mock_assign, \
         patch("data.chunking.extract_chunk_plugins.build_chunk_dict") as mock_build:
        mock_assign.return_value = [{"chunk_text": "chunk1", "code_blocks": []}]
        mock_build.return_value = "chunk dict"

        result = process_plugin(plugin_name, html, text_splitter)

        mock_logger.warning.assert_called_once()
        assert "no placeholders found" in mock_logger.warning.call_args[0][0]
        assert result == ["chunk dict"]


@patch("data.chunking.extract_chunk_plugins.process_plugin")
@patch("data.chunking.extract_chunk_plugins.get_text_splitter")
def test_extract_chunks_aggregates_chunks(mock_get_splitter, mock_process_plugin):
    """Test extract_chunks aggregates all plugin chunks."""
    docs = {
        "PluginA": "<html></html>",
        "PluginB": "<html></html>"
    }
    mock_get_splitter.return_value = "splitter"
    mock_process_plugin.side_effect = [
        ["chunkA1", "chunkA2"],
        ["chunkB1"]
    ]

    result = extract_chunks(docs)

    mock_get_splitter.assert_called_once_with(500, 100)
    assert mock_process_plugin.call_count == 2
    assert result == ["chunkA1", "chunkA2", "chunkB1"]
