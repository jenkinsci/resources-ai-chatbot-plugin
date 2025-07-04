"""Unit tests for LlamaCppProvider."""

from unittest.mock import patch, MagicMock
import pytest
from api.models.llama_cpp_provider import LlamaCppProvider


@patch("api.models.llama_cpp_provider.Llama")
def test_generate_success(mock_llama_class):
    """Test that generate returns expected text."""
    mock_instance = MagicMock()
    mock_instance.return_value = {"choices": [{"text": "This is a test."}]}
    mock_llama_class.return_value = mock_instance

    provider = LlamaCppProvider()
    response = provider.generate("Say hi", max_tokens=10)

    mock_instance.assert_called_once()
    assert response == "This is a test."


@patch("api.models.llama_cpp_provider.Llama")
def test_generate_invalid_model_config(mock_llama_class):
    """Test that generate raises RuntimeError on ValueError."""
    mock_instance = MagicMock()
    mock_instance.side_effect = ValueError("Invalid path")
    mock_llama_class.return_value = mock_instance

    provider = LlamaCppProvider()
    with pytest.raises(RuntimeError) as excinfo:
        provider.generate("Prompt", max_tokens=10)

    assert "LLM model could not be initialized. Check the model path." in str(excinfo.value)


@patch("api.models.llama_cpp_provider.Llama")
def test_generate_generic_exception(mock_llama_class):
    """Test that generate returns fallback message on error."""
    mock_instance = MagicMock()
    mock_instance.side_effect = Exception("Exc")
    mock_llama_class.return_value = mock_instance

    provider = LlamaCppProvider()
    result = provider.generate("Prompt", max_tokens=10)

    assert "Sorry, something went wrong during generation." in result
