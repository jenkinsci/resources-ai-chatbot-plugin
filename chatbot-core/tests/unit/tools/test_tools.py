"""Unit tests for the agentic tools."""
from unittest.mock import patch, MagicMock
import httpx
from api.tools.tools import fetch_jenkins_build_logs


@patch("api.tools.tools.httpx.get")
@patch("api.tools.tools.sanitize_logs")
def test_fetch_jenkins_build_logs_success(mock_sanitize, mock_get):
    """Test successful log fetch and sanitization, verifying URL construction."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "Raw log data"
    mock_sanitize.return_value = "Sanitized logs for my-backend-job #42"

    mock_logger = MagicMock()
    result = fetch_jenkins_build_logs(
        "my-backend-job", "42", logger=mock_logger)

    assert "Sanitized logs" in result

    # 3. Verify exact URL construction (Fixes Guna's 3rd comment)
    mock_get.assert_called_once_with(
        "http://localhost:8080/job/my-backend-job/42/consoleText",
        auth=None,
        timeout=10.0
    )


# 4. Add the missing error path tests (Fixes Guna's 4th comment)

@patch("api.tools.tools.httpx.get")
def test_fetch_jenkins_build_logs_auth_failure(mock_get):
    """Test 401/403 authentication failures."""
    mock_get.return_value.status_code = 403

    mock_logger = MagicMock()
    result = fetch_jenkins_build_logs(
        "my-backend-job", "42", logger=mock_logger)

    assert "Authentication failed" in result
    assert "JENKINS_USER and JENKINS_TOKEN" in result


@patch("api.tools.tools.httpx.get")
def test_fetch_jenkins_build_logs_not_found(mock_get):
    """Test 404 not found using 'lastFailedBuild'."""
    mock_get.return_value.status_code = 404

    mock_logger = MagicMock()
    result = fetch_jenkins_build_logs(
        "invalid-job", "lastFailedBuild", logger=mock_logger)

    assert "Logs not found for job 'invalid-job'" in result


@patch("api.tools.tools.httpx.get")
def test_fetch_jenkins_build_logs_network_error(mock_get):
    """Test network timeout/request errors."""
    mock_get.side_effect = httpx.RequestError("Network timeout")

    mock_logger = MagicMock()
    result = fetch_jenkins_build_logs("my-job", "1", logger=mock_logger)

    # Because tools.py catches the error and returns a formatted string:
    assert "Failed to connect to Jenkins server" in result
