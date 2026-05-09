"""Unit tests for query type utility functions in api/models/schemas.py."""
import pytest
from api.models.schemas import (
    QueryType,
    is_valid_query_type,
    str_to_query_type,
    try_str_to_query_type,
)


def test_is_valid_query_type_returns_true_for_simple():
    """Test that is_valid_query_type returns True for SIMPLE."""
    assert is_valid_query_type("SIMPLE") is True


def test_is_valid_query_type_returns_true_for_multi():
    """Test that is_valid_query_type returns True for MULTI."""
    assert is_valid_query_type("MULTI") is True


def test_is_valid_query_type_returns_false_for_invalid():
    """Test that is_valid_query_type returns False for invalid strings."""
    assert is_valid_query_type("INVALID") is False


def test_is_valid_query_type_returns_false_for_empty_string():
    """Test that is_valid_query_type returns False for empty string."""
    assert is_valid_query_type("") is False


def test_is_valid_query_type_case_sensitive():
    """Test that is_valid_query_type is case sensitive."""
    assert is_valid_query_type("simple") is False
    assert is_valid_query_type("multi") is False


def test_str_to_query_type_converts_simple():
    """Test that str_to_query_type converts SIMPLE to QueryType.SIMPLE."""
    assert str_to_query_type("SIMPLE") == QueryType.SIMPLE


def test_str_to_query_type_converts_multi():
    """Test that str_to_query_type converts MULTI to QueryType.MULTI."""
    assert str_to_query_type("MULTI") == QueryType.MULTI


def test_str_to_query_type_raises_value_error_for_invalid():
    """Test that str_to_query_type raises ValueError for invalid input."""
    with pytest.raises(ValueError, match="Invalid query type: UNKNOWN"):
        str_to_query_type("UNKNOWN")


def test_str_to_query_type_raises_value_error_for_empty():
    """Test that str_to_query_type raises ValueError for empty string."""
    with pytest.raises(ValueError):
        str_to_query_type("")


def test_try_str_to_query_type_returns_simple(mocker):
    """Test that try_str_to_query_type returns SIMPLE for valid input."""
    mock_logger = mocker.MagicMock()
    result = try_str_to_query_type("SIMPLE", mock_logger)
    assert result == QueryType.SIMPLE
    mock_logger.info.assert_not_called()


def test_try_str_to_query_type_returns_multi(mocker):
    """Test that try_str_to_query_type returns MULTI for valid input."""
    mock_logger = mocker.MagicMock()
    result = try_str_to_query_type("MULTI", mock_logger)
    assert result == QueryType.MULTI
    mock_logger.info.assert_not_called()


def test_try_str_to_query_type_falls_back_to_multi_on_invalid(mocker):
    """Test that try_str_to_query_type falls back to MULTI for invalid input."""
    mock_logger = mocker.MagicMock()
    result = try_str_to_query_type("INVALID", mock_logger)
    assert result == QueryType.MULTI


def test_try_str_to_query_type_logs_warning_on_invalid(mocker):
    """Test that try_str_to_query_type logs a warning for invalid input."""
    mock_logger = mocker.MagicMock()
    try_str_to_query_type("INVALID", mock_logger)
    mock_logger.info.assert_called_once()


def test_try_str_to_query_type_falls_back_on_empty_string(mocker):
    """Test that try_str_to_query_type falls back to MULTI for empty string."""
    mock_logger = mocker.MagicMock()
    result = try_str_to_query_type("", mock_logger)
    assert result == QueryType.MULTI
