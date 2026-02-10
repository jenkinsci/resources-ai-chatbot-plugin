"""Unit tests for the sanitizer module."""
import unittest
from api.tools.sanitizer import sanitize_logs

class TestLogSanitizer(unittest.TestCase):
    """Test suite for log sanitization to ensure secrets are redacted."""

    def test_sanitize_password_assignment(self):
        """Test that simple password assignments are redacted."""
        log = "Connecting to DB with password=superSecretPassword123!"
        expected = "Connecting to DB with password=[REDACTED]"
        self.assertEqual(sanitize_logs(log), expected)

    def test_sanitize_docker_login(self):
        """Test that docker login passwords are redacted."""
        log = "docker login -u user -p myRealPassword123 registry.com"
        # We expect the flag content to be masked
        result = sanitize_logs(log)
        self.assertNotIn("myRealPassword123", result)
        self.assertIn("[REDACTED]", result)

    def test_sanitize_aws_key(self):
        """Test that AWS access keys are redacted."""
        log = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"
        result = sanitize_logs(log)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", result)
        self.assertIn("[REDACTED_AWS_KEY]", result)

    def test_no_false_positives(self):
        """Test that normal logs without secrets remain unchanged."""
        log = "Build step 'Execute Windows batch command' marked build as failure"
        self.assertEqual(sanitize_logs(log), log)

if __name__ == '__main__':
    unittest.main()
