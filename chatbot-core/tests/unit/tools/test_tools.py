"""Unit tests for the agentic tools."""
from unittest.mock import patch, MagicMock
from api.tools.tools import fetch_jenkins_build_logs


@patch("api.tools.tools.sanitize_logs")
@patch("api.tools.tools.httpx.get")
def test_fetch_jenkins_build_logs_success(mock_get, mock_sanitize):
    """Test that the Jenkins fetcher correctly grabs and sanitizes logs."""

    # 1. Setup a fake Jenkins HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "Raw Jenkins Log with [INFO] noise..."
    mock_get.return_value = mock_response

    # 2. Setup a fake sanitized output
    mock_sanitize.return_value = "Cleaned Error Log"
    mock_logger = MagicMock()

    # 3. Call our new function
    result = fetch_jenkins_build_logs("my-backend-job", "42", mock_logger)

    # 4. Verify it worked perfectly
    assert "Sanitized logs for my-backend-job #42" in result
    assert "Cleaned Error Log" in result
    mock_get.assert_called_once()
    mock_sanitize.assert_called_once_with(
        "Raw Jenkins Log with [INFO] noise...")
