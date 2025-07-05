"""Unit Tests for the extract_functions module."""

from bs4 import BeautifulSoup
from data.chunking.chunking_utils import (
    extract_title,
    extract_code_blocks,
    assign_code_blocks_to_chunks
)

def test_extract_title_h1_present():
    """Test that the title is succesfully extracted from h1."""
    html = "<html><head><title>Title</title></head><body><h1>Header Title</h1></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    result = extract_title(soup)
    assert result == "Header Title"


def test_extract_title_h1_empty_title_fallback():
    """Test that the title is extracted from the head if h1 is empty."""
    html = "<html><head><title>Fallback Title</title></head><body><h1>   </h1></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    result = extract_title(soup)
    assert result == "Fallback Title"


def test_extract_title_no_h1_no_title():
    """Test that if no title is detected it returns the fallback title."""
    html = "<html><body><p>No headers here</p></body></html>"
    soup = BeautifulSoup(html, "html.parser")
    result = extract_title(soup)
    assert result == "Untitled"


def test_extract_code_blocks_replaces_code_with_placeholders():
    """Test that it successfully replace the code blocks with a given placeholder."""
    html = """
    <div><pre>code block one</pre><pre>code block two</pre></div>
    """
    soup = BeautifulSoup(html, "html.parser")
    placeholder_template = "[[CODE_{0}]]"
    tag_to_search = "pre"
    code_blocks = extract_code_blocks(soup, tag_to_search, placeholder_template)

    assert code_blocks == ["code block one", "code block two"]
    placeholders = [str(el) for el in soup.div.children if el.name is None]
    assert "[[CODE_0]]" in placeholders[0]
    assert "[[CODE_1]]" in placeholders[1]


def test_assign_code_blocks_to_chunks_basic_match(mocker):
    """Test that it associates code blocks when valid placeholders are present."""
    chunks = [
        "Some text [[CODE_0]] more text [[CODE_1]] end."
    ]
    code_blocks = ["code A", "code B"]
    pattern = r"\[\[CODE_(\d+)\]\]"
    logger = mocker.Mock()

    result = assign_code_blocks_to_chunks(chunks, code_blocks, pattern, logger)
    assert len(result) == 1
    assert result[0]["chunk_text"] == chunks[0]
    assert result[0]["code_blocks"] == ["code A", "code B"]
    logger.warning.assert_not_called()


def test_assign_code_blocks_to_chunks_out_of_range(mocker):
    """Test that it logs a warning when placeholder index is out of range."""
    chunks = ["Text with [[CODE_2]] placeholder."]
    code_blocks = ["only one"]
    pattern = r"\[\[CODE_(\d+)\]\]"
    logger = mocker.Mock()

    result = assign_code_blocks_to_chunks(chunks, code_blocks, pattern, logger)
    assert len(result) == 1
    assert result[0]["code_blocks"] == []
    logger.warning.assert_called_once()
    assert "out of range" in logger.warning.call_args[0][0]


def test_assign_code_blocks_to_chunks_malformed_placeholder(mocker):
    """Test that a log warning is printed when placeholder index is invalid."""
    chunks = ["Text with [[CODE_XYZ]] placeholder."]
    code_blocks = ["some code"]
    pattern = r"\[\[CODE_(\w+)\]\]"
    logger = mocker.Mock()

    result = assign_code_blocks_to_chunks(chunks, code_blocks, pattern, logger)
    assert len(result) == 1
    assert result[0]["code_blocks"] == []
    logger.warning.assert_called_once()
    assert "Malformed" in logger.warning.call_args[0][0]


def test_assign_code_blocks_to_chunks_no_placeholders(mocker):
    """Test that asserts the correct handling of chunks without any placeholders."""
    chunks = ["Plain text with no placeholders."]
    code_blocks = ["some code"]
    pattern = r"\[\[CODE_(\d+)\]\]"
    logger = mocker.Mock()

    result = assign_code_blocks_to_chunks(chunks, code_blocks, pattern, logger)
    assert len(result) == 1
    assert result[0]["chunk_text"] == chunks[0]
    assert result[0]["code_blocks"] == []
    logger.warning.assert_not_called()
