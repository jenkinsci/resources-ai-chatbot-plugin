"""Unit tests for query-type helpers and request validators in schemas.py."""
# pylint: disable=redefined-outer-name

import logging

import pytest

from api.models.schemas import (
    ChatRequest,
    ChatRequestWithFiles,
    FileAttachment,
    FileType,
    QueryType,
    is_valid_query_type,
    str_to_query_type,
    try_str_to_query_type,
)


class TestIsValidQueryType:
    """is_valid_query_type should accept only exact enum member names."""

    def test_simple_is_valid(self):
        """SIMPLE is a recognised member."""
        assert is_valid_query_type("SIMPLE") is True

    def test_multi_is_valid(self):
        """MULTI is a recognised member."""
        assert is_valid_query_type("MULTI") is True

    def test_lowercase_rejected(self):
        """Enum lookup is case-sensitive."""
        assert is_valid_query_type("simple") is False

    def test_empty_string_rejected(self):
        """Empty string is not a member."""
        assert is_valid_query_type("") is False

    def test_unknown_string_rejected(self):
        """Arbitrary strings must be rejected."""
        assert is_valid_query_type("COMPLEX") is False


class TestStrToQueryType:
    """str_to_query_type converts valid strings or raises ValueError."""

    def test_converts_simple(self):
        """SIMPLE string maps to QueryType.SIMPLE."""
        assert str_to_query_type("SIMPLE") == QueryType.SIMPLE

    def test_converts_multi(self):
        """MULTI string maps to QueryType.MULTI."""
        assert str_to_query_type("MULTI") == QueryType.MULTI

    def test_invalid_string_raises(self):
        """Unrecognised input raises ValueError."""
        with pytest.raises(ValueError, match="Invalid query type"):
            str_to_query_type("UNKNOWN")

    def test_empty_string_raises(self):
        """Empty input raises ValueError."""
        with pytest.raises(ValueError, match="Invalid query type"):
            str_to_query_type("")


class TestTryStrToQueryType:
    """try_str_to_query_type falls back to MULTI on bad input."""

    @pytest.fixture()
    def logger(self):
        """Provide a logger for the function under test."""
        return logging.getLogger("test_schemas")

    def test_valid_simple(self, logger):
        """Valid SIMPLE string converts normally."""
        assert try_str_to_query_type("SIMPLE", logger) == QueryType.SIMPLE

    def test_valid_multi(self, logger):
        """Valid MULTI string converts normally."""
        assert try_str_to_query_type("MULTI", logger) == QueryType.MULTI

    def test_invalid_falls_back_to_multi(self, logger):
        """Bad input defaults to MULTI instead of crashing."""
        assert try_str_to_query_type("garbage", logger) == QueryType.MULTI

    def test_empty_falls_back_to_multi(self, logger):
        """Empty string defaults to MULTI."""
        assert try_str_to_query_type("", logger) == QueryType.MULTI


class TestChatRequestValidation:
    """ChatRequest.message validator rejects empty/whitespace messages."""

    def test_normal_message_accepted(self):
        """Regular text passes validation."""
        req = ChatRequest(message="Hello Jenkins!")
        assert req.message == "Hello Jenkins!"

    def test_empty_string_rejected(self):
        """Empty string is not a valid message."""
        with pytest.raises(ValueError, match="Message cannot be empty"):
            ChatRequest(message="")

    def test_whitespace_only_rejected(self):
        """Spaces-only message is treated as empty."""
        with pytest.raises(ValueError, match="Message cannot be empty"):
            ChatRequest(message="   ")


class TestChatRequestWithFilesValidation:
    """ChatRequestWithFiles requires at least a message or a file."""

    @pytest.fixture()
    def sample_attachment(self):
        """Minimal valid file attachment for reuse across tests."""
        return FileAttachment(
            filename="readme.txt",
            type=FileType.TEXT,
            content="hello",
            mime_type="text/plain",
        )

    def test_message_only(self):
        """Message without files is fine."""
        req = ChatRequestWithFiles(message="Hi")
        assert req.message == "Hi"

    def test_files_only(self, sample_attachment):
        """Files without a message is fine."""
        req = ChatRequestWithFiles(message="", files=[sample_attachment])
        assert len(req.files) == 1

    def test_both_message_and_files(self, sample_attachment):
        """Both provided together should work."""
        req = ChatRequestWithFiles(message="Analyze this", files=[sample_attachment])
        assert req.message == "Analyze this"

    def test_no_message_no_files_rejected(self):
        """Sending neither message nor files is invalid."""
        with pytest.raises(ValueError, match="Either message or files must be provided"):
            ChatRequestWithFiles(message="", files=None)

    def test_whitespace_message_no_files_rejected(self):
        """Whitespace-only message with no files is invalid."""
        with pytest.raises(ValueError, match="Either message or files must be provided"):
            ChatRequestWithFiles(message="   ", files=None)

    def test_empty_files_list_no_message_rejected(self):
        """Empty list counts the same as None for files."""
        with pytest.raises(ValueError, match="Either message or files must be provided"):
            ChatRequestWithFiles(message="", files=[])
