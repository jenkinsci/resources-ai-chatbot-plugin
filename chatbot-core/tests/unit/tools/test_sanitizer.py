"""Unit tests for the sanitizer module."""

import unittest

from api.tools.sanitizer import sanitize_logs


class TestLogSanitizer(unittest.TestCase):
    """Test suite for log sanitization to ensure secrets are redacted."""

    def assert_sanitized(self, raw, expected):
        """
        Assert a log string sanitizes to the expected output.

        Args:
            raw (str): Input log text.
            expected (str): Expected sanitized text.
        """
        self.assertEqual(sanitize_logs(raw), expected)

    def test_sanitize_secret_assignments(self):
        """Test that common secret assignments are redacted."""
        cases = [
            ("TOKEN=abc123", "TOKEN=[REDACTED]"),
            ('TOKEN="abc\\"def"', 'TOKEN="[REDACTED]"'),
            ("password: abc123", "password: [REDACTED]"),
            ("PASSWORD=${MY_PASSWORD}", "PASSWORD=[REDACTED]"),
            ("MY_SECRET='abc123'", "MY_SECRET='[REDACTED]'"),
            ('"api_key": "abc123"', '"api_key": "[REDACTED]"'),
            (
                "BITBUCKET_COMMON_CREDS_PSW=abc123",
                "BITBUCKET_COMMON_CREDS_PSW=[REDACTED]",
            ),
        ]

        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assert_sanitized(raw, expected)

    def test_sanitize_docker_login(self):
        """Test that docker login passwords are redacted."""
        cases = [
            (
                "docker login -u user -p myRealPassword123 registry.com",
                "docker login -u user -p [REDACTED] registry.com",
            ),
            (
                "docker login -u user --password myRealPassword123 registry.com",
                "docker login -u user --password [REDACTED] registry.com",
            ),
            (
                "docker login -u user --password=myRealPassword123 registry.com",
                "docker login -u user --password=[REDACTED] registry.com",
            ),
            (
                "docker login -u user --password-stdin registry.com",
                "docker login -u user --password-stdin registry.com",
            ),
        ]

        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assert_sanitized(raw, expected)

    def test_sanitize_headers_and_url_secrets(self):
        """Test that HTTP headers, URL passwords, and query secrets are redacted."""
        cases = [
            ("Authorization: Bearer abc123", "Authorization: [REDACTED]"),
            ("X-API-Key: abc123", "X-API-Key: [REDACTED]"),
            ("Cookie: session=abcdef", "Cookie: [REDACTED]"),
            (
                "https://user:password@example.com/repository",
                "https://user:[REDACTED]@example.com/repository",
            ),
            (
                "https://example.com?a=1&token=abc123&debug=true",
                "https://example.com?a=1&token=[REDACTED]&debug=true",
            ),
            (
                'curl "https://example.com?token=abc123"',
                'curl "https://example.com?token=[REDACTED]"',
            ),
        ]

        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assert_sanitized(raw, expected)

    def test_sanitize_known_token_formats(self):
        """Test that recognizable raw token formats are redacted."""
        cases = [
            ("AKIAIOSFODNN7EXAMPLE", "[REDACTED_AWS_KEY]"),
            (
                "ghp_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6",
                "[REDACTED_GITHUB_TOKEN]",
            ),
            ("sk-abcdefghijklmnopqrstuvwxyz123456", "[REDACTED_API_KEY]"),
            (
                "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.sig",
                "[REDACTED_JWT]",
            ),
        ]

        for raw, expected in cases:
            with self.subTest(raw=raw):
                self.assert_sanitized(raw, expected)

    def test_sanitize_private_key(self):
        """Test that private key blocks are redacted."""
        raw = (
            "Found key:\n"
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "someBase64ContentHere\n"
            "-----END RSA PRIVATE KEY-----"
        )
        expected = "Found key:\n[REDACTED_PRIVATE_KEY]"

        self.assert_sanitized(raw, expected)

    def test_no_false_positives_for_common_diagnostics(self):
        """Test that normal logs without secrets remain unchanged."""
        cases = [
            "Build step 'Execute Windows batch command' marked build as failure",
            "PWD=/var/lib/jenkins/workspace/project",
            "credentialsId: 'docker-production'",
            "token_count=5",
            "git clone git@github.com:jenkinsci/plugin.git",
        ]

        for raw in cases:
            with self.subTest(raw=raw):
                self.assert_sanitized(raw, raw)

    def test_is_idempotent(self):
        """Test that running the sanitizer twice does not change the result."""
        raw = (
            "TOKEN=abc123\n"
            "Authorization: Bearer xyz456\n"
            "https://user:password@example.com/repository"
        )
        sanitized = sanitize_logs(raw)

        self.assert_sanitized(sanitized, sanitized)


if __name__ == "__main__":
    unittest.main()
