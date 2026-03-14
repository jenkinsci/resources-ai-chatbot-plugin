"""Unit Tests for extract_chunk_plugins module."""
# pylint: disable=import-error, redefined-outer-name, unused-argument

from unittest.mock import Mock, patch
import pytest
from data.chunking.extract_chunk_plugins import PluginsChunker

@pytest.fixture
def plugins_chunker():
    """Returns a PluginsChunker instance."""
    return PluginsChunker()

@patch("data.chunking.extract_chunk_plugins.build_chunk_dict")
@patch("data.chunking.extract_chunk_plugins.assign_code_blocks_to_chunks")
@patch("data.chunking.extract_chunk_plugins.extract_code_blocks")
def test_process_plugin_returns_chunks(
    mock_extract_code,
    mock_assign_chunks,
    mock_build_chunk,
    plugins_chunker
):
    """Test that it extracts code blocks, splits text,assigns code blocks to chunks."""
    plugin_name = "Test Plugin"
    html = "<html><body><pre>code</pre></body></html>"
    plugins_chunker.text_splitter = Mock()
    plugins_chunker.text_splitter.split_text.return_value = ["chunk1"]

    mock_extract_code.return_value = ["code block"]
    mock_assign_chunks.return_value = [
        {"chunk_text": "chunk1", "code_blocks": ["code block"]}
    ]
    mock_build_chunk.return_value = "chunk dict"

    result = plugins_chunker.process_plugin(plugin_name, html)

    mock_extract_code.assert_called_once()
    plugins_chunker.text_splitter.split_text.assert_called_once()
    mock_assign_chunks.assert_called_once()
    mock_build_chunk.assert_called_once()
    assert result == ["chunk dict"]


@patch("data.chunking.extract_chunk_plugins.assign_code_blocks_to_chunks", return_value=[])
@patch("data.chunking.extract_chunk_plugins.extract_code_blocks")
def test_process_plugin_logs_warning_on_missing_placeholder(
    mock_extract_code,
    _mock_assign_chunks,
    plugins_chunker
):
    """Test process_plugin logs a warning if code is found but no placeholder is in the text."""
    plugin_name = "PluginX"
    html = "<html><body><pre>some code</pre></body></html>"
    plugins_chunker.text_splitter = Mock()
    plugins_chunker.text_splitter.split_text.return_value = ["chunk without placeholder"]
    plugins_chunker.logger = Mock()
    mock_extract_code.return_value = ["some code"]

    plugins_chunker.process_plugin(plugin_name, html)

    plugins_chunker.logger.warning.assert_called_once()
    assert "no placeholders found" in plugins_chunker.logger.warning.call_args[0][0]


@patch("data.chunking.extract_chunk_plugins.PluginsChunker.process_plugin")
def test_extract_chunks_aggregates_chunks(mock_process_plugin, plugins_chunker):
    """Test extract_chunks aggregates all plugin chunks."""
    docs = {
        "PluginA": "<html></html>",
        "PluginB": "<html></html>"
    }
    mock_process_plugin.side_effect = [
        ["chunkA1", "chunkA2"],
        ["chunkB1"]
    ]

    result = plugins_chunker.extract_chunks(docs)

    assert mock_process_plugin.call_count == 2
    assert result == ["chunkA1", "chunkA2", "chunkB1"]
