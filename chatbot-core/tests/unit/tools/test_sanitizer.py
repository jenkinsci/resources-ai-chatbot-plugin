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

    # The patterns below exist in sanitizer.py but had no tests.

    def test_sanitize_bearer_token(self):
        """Bearer tokens should be replaced with [REDACTED_TOKEN]."""
        log = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig"
        result = sanitize_logs(log)
        self.assertNotIn("eyJhbGciOiJIUzI1NiJ9", result)
        self.assertIn("[REDACTED_TOKEN]", result)

    def test_sanitize_github_token(self):
        """GitHub PATs (ghp_...) should be replaced with [REDACTED_GITHUB_TOKEN]."""
        log = "GITHUB_TOKEN=ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
        result = sanitize_logs(log)
        self.assertNotIn("ghp_ABCDEF", result)
        self.assertIn("[REDACTED_GITHUB_TOKEN]", result)

    def test_sanitize_private_key_block(self):
        """PEM private key blocks should be replaced with [REDACTED_PRIVATE_KEY]."""
        log = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIBogIBAAJBAKxL\n"
            "-----END RSA PRIVATE KEY-----"
        )
        result = sanitize_logs(log)
        self.assertNotIn("MIIBogIBAAJBAKxL", result)
        self.assertIn("[REDACTED_PRIVATE_KEY]", result)

    def test_sanitize_client_secret(self):
        """client_secret=... should be redacted like other password-style keys."""
        log = "client_secret=superSecretOAuthValue"
        result = sanitize_logs(log)
        self.assertNotIn("superSecretOAuthValue", result)
        self.assertIn("[REDACTED]", result)

    def test_sanitize_api_key_with_colon(self):
        """api_key: ... (colon separator) should also be caught."""
        log = "api_key: sk-proj-1234567890abcdef"
        result = sanitize_logs(log)
        self.assertNotIn("sk-proj-1234567890abcdef", result)
        self.assertIn("[REDACTED]", result)

if __name__ == '__main__':
    unittest.main()
