"""
Unit tests for PII sanitization service.

These tests prove that sensitive information is never leaked to the LLM.
"""

import pytest
from api.services.sanitizer import (
    sanitize_log,
    sanitize_log_simple,
    get_pattern_names,
)


class TestSanitizeAwsCredentials:
    """Tests for AWS credential sanitization."""

    def test_sanitizes_aws_access_key(self):
        """AWS Access Key IDs like AKIAIOSFODNN7EXAMPLE are masked."""
        log = "Using AWS_ACCESS_KEY_ID: AKIAIOSFODNN7EXAMPLE"
        sanitized, patterns = sanitize_log(log)

        assert "AKIAIOSFODNN7EXAMPLE" not in sanitized
        assert "[AWS_KEY_REDACTED]" in sanitized
        assert "aws_access_key" in patterns

    def test_sanitizes_aws_secret_key(self):
        """AWS Secret Access Keys are masked."""
        log = "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        sanitized, patterns = sanitize_log(log)

        assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in sanitized
        assert "[AWS_SECRET_REDACTED]" in sanitized

    def test_sanitizes_aws_access_key_asia(self):
        """AWS temporary credentials (ASIA prefix) are masked."""
        log = "Access Key: ASIAJEXAMPLEKEYID12"
        sanitized, _ = sanitize_log(log)

        assert "ASIAJEXAMPLEKEYID12" not in sanitized


class TestSanitizeGitHubTokens:
    """Tests for GitHub token sanitization."""

    def test_sanitizes_github_pat(self):
        """GitHub Personal Access Tokens (ghp_) are masked."""
        log = "Using token: ghp_1234567890abcdefghijklmnopqrstuvwxyz12"
        sanitized, patterns = sanitize_log(log)

        assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz12" not in sanitized
        assert "[GITHUB_TOKEN_REDACTED]" in sanitized
        assert "github_token" in patterns

    def test_sanitizes_github_oauth_token(self):
        """GitHub OAuth tokens (gho_) are masked."""
        log = "GITHUB_TOKEN=gho_abcdefghijklmnopqrstuvwxyz1234567890"
        sanitized, _ = sanitize_log(log)

        assert "gho_abcdefghijklmnopqrstuvwxyz1234567890" not in sanitized


class TestSanitizePasswords:
    """Tests for password sanitization."""

    def test_sanitizes_password_in_url(self):
        """user:password@host patterns in URLs are masked."""
        log = "Connecting to https://admin:super_secret_pass@db.example.com/mydb"
        sanitized, patterns = sanitize_log(log)

        assert "admin" not in sanitized
        assert "super_secret_pass" not in sanitized
        assert "[USER_REDACTED]" in sanitized
        assert "[PASSWORD_REDACTED]" in sanitized
        assert "url_password" in patterns

    def test_sanitizes_password_assignment(self):
        """Password assignments (password=value) are masked."""
        log = "Setting password=my_secret_password123"
        sanitized, patterns = sanitize_log(log)

        assert "my_secret_password123" not in sanitized
        assert "password_assignment" in patterns

    def test_sanitizes_passwd_variants(self):
        """Various password field names are detected."""
        log = """
        passwd: db_password_here
        pwd = another_secret
        secret: very_hidden_value
        """
        sanitized, _ = sanitize_log(log)

        assert "db_password_here" not in sanitized
        assert "another_secret" not in sanitized
        assert "very_hidden_value" not in sanitized


class TestSanitizeTokens:
    """Tests for token sanitization."""

    def test_sanitizes_bearer_token(self):
        """Bearer tokens are masked."""
        log = "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test"
        sanitized, patterns = sanitize_log(log)

        assert "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized
        assert "Bearer [TOKEN_REDACTED]" in sanitized
        assert "bearer_token" in patterns

    def test_sanitizes_jwt_token(self):
        """JWT tokens (three base64 parts) are masked."""
        # Standard JWT format
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.abc123_signature"
        log = f"Token: {jwt}"
        sanitized, patterns = sanitize_log(log)

        assert "eyJhbGciOiJIUzI1NiJ9" not in sanitized
        assert "[JWT_REDACTED]" in sanitized
        assert "jwt_token" in patterns

    def test_sanitizes_generic_api_key(self):
        """Generic API keys are masked."""
        log = "api_key = sk_live_1234567890abcdefghij"
        sanitized, patterns = sanitize_log(log)

        assert "sk_live_1234567890abcdefghij" not in sanitized
        assert "[API_KEY_REDACTED]" in sanitized
        assert "generic_api_key" in patterns


class TestSanitizePrivateKeys:
    """Tests for private key sanitization."""

    def test_sanitizes_rsa_private_key(self):
        """RSA private keys are fully masked."""
        log = """
        Attempting to use key:
        -----BEGIN RSA PRIVATE KEY-----
        MIIEowIBAAKCAQEA0m59l2u9iDnMbrXHfqkOrn2dVQ3vfBJqcDuFUK03d+1PZGbV
        yBn3SXiDj/+4V8XBLC+HM4oVe2J3ZwDpKMHpfQRZhLR8f8VJX3dW7p+wuXDY7p0A
        ...more key data...
        -----END RSA PRIVATE KEY-----
        """
        sanitized, patterns = sanitize_log(log)

        assert "MIIEowIBAAKCAQEA0m59l2u9iDnMbrXHfqkOrn2dVQ3vfBJqcDuFUK03d" not in sanitized
        assert "[PRIVATE_KEY_REDACTED]" in sanitized
        assert "private_key" in patterns

    def test_sanitizes_openssh_private_key(self):
        """OpenSSH private keys are masked."""
        log = """
        -----BEGIN OPENSSH PRIVATE KEY-----
        b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAlwAAAAdzc2gtcn
        -----END OPENSSH PRIVATE KEY-----
        """
        sanitized, patterns = sanitize_log(log)

        assert "b3BlbnNzaC1rZXktdjE" not in sanitized
        assert "[SSH_KEY_REDACTED]" in sanitized
        assert "ssh_key" in patterns


class TestSanitizeOtherSecrets:
    """Tests for other secret types."""

    def test_sanitizes_jenkins_token(self):
        """Jenkins API tokens are masked."""
        log = "JENKINS_API_TOKEN=11e4a6c8d2f8b9e1a3c5d7f9b0e2a4c6d8f0"
        sanitized, patterns = sanitize_log(log)

        assert "11e4a6c8d2f8b9e1a3c5d7f9b0e2a4c6d8f0" not in sanitized
        assert "[JENKINS_TOKEN_REDACTED]" in sanitized
        assert "jenkins_token" in patterns

    def test_sanitizes_slack_token(self):
        """Slack tokens are masked."""
        # Using clearly fake test values (FAKE prefix indicates test data)
        log = "SLACK_TOKEN=xoxb-FAKE-FAKE-TESTTOKEN"
        sanitized, patterns = sanitize_log(log)

        assert "xoxb-FAKE-FAKE-TESTTOKEN" not in sanitized
        assert "[SLACK_TOKEN_REDACTED]" in sanitized
        assert "slack_token" in patterns

    def test_sanitizes_npm_token(self):
        """NPM tokens are masked."""
        log = "//registry.npmjs.org/:_authToken=npm_1234567890abcdefghijklmnopqrstuv"
        sanitized, patterns = sanitize_log(log)

        assert "npm_1234567890abcdefghijklmnopqrstuv" not in sanitized
        assert "[NPM_TOKEN_REDACTED]" in sanitized
        assert "npm_token" in patterns

    def test_sanitizes_base64_credentials(self):
        """Base64 encoded credentials are masked."""
        # Simulating Basic auth encoding
        log = 'basic: dXNlcm5hbWU6cGFzc3dvcmQxMjM0NTY3ODkwMTIzNDU2Nzg5MA=='
        sanitized, patterns = sanitize_log(log)

        assert "dXNlcm5hbWU6cGFzc3dvcmQxMjM0NTY3ODkwMTIzNDU2Nzg5MA==" not in sanitized
        assert "[BASE64_CREDENTIALS_REDACTED]" in sanitized

    def test_sanitizes_export_secrets(self):
        """Export statements with secrets are masked."""
        log = "export API_KEY_PROD=my_super_secret_key_12345"
        sanitized, patterns = sanitize_log(log)

        assert "my_super_secret_key_12345" not in sanitized
        assert "export_secret" in patterns


class TestPreservesSafeContent:
    """Tests that safe content is preserved."""

    def test_preserves_error_messages(self):
        """Error messages without secrets are preserved."""
        log = """
        [ERROR] Build failed at step 3
        [ERROR] NullPointerException in MyClass.java:42
        [FATAL] Cannot connect to database
        """
        sanitized, patterns = sanitize_log(log)

        # No secrets detected
        assert len(patterns) == 0

        # Content preserved
        assert "Build failed at step 3" in sanitized
        assert "NullPointerException" in sanitized
        assert "Cannot connect to database" in sanitized

    def test_preserves_stack_traces(self):
        """Stack traces without secrets are preserved."""
        log = """
        java.lang.NullPointerException
            at com.example.MyClass.myMethod(MyClass.java:42)
            at com.example.Main.main(Main.java:10)
        """
        sanitized, _ = sanitize_log(log)

        assert "NullPointerException" in sanitized
        assert "MyClass.java:42" in sanitized
        assert "Main.java:10" in sanitized

    def test_preserves_maven_output(self):
        """Maven build output is preserved."""
        log = """
        [INFO] Building my-project 1.0.0
        [INFO] --- maven-compiler-plugin:3.8.1:compile (default-compile) @ my-project ---
        [ERROR] Failed to execute goal: Could not resolve dependencies
        """
        sanitized, _ = sanitize_log(log)

        assert "Building my-project 1.0.0" in sanitized
        assert "maven-compiler-plugin" in sanitized
        assert "Could not resolve dependencies" in sanitized


class TestMixedContent:
    """Tests with mixed secret and non-secret content."""

    def test_sanitizes_secrets_in_real_log(self):
        """Real-world log with mixed content."""
        log = """
        [INFO] Starting build #123
        [INFO] Checking out from git@github.com:org/repo.git
        [INFO] Using credentials from environment
        AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
        AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEX
        [ERROR] Build failed: NullPointerException at MyClass.java:42
        [INFO] Uploading artifacts...
        Using API key: sk_live_12345678901234567890
        [ERROR] Upload failed: Connection refused
        """
        sanitized, patterns = sanitize_log(log)

        # Secrets are masked
        assert "AKIAIOSFODNN7EXAMPLE" not in sanitized
        assert "wJalrXUtnFEMI" not in sanitized
        assert "sk_live_12345678901234567890" not in sanitized

        # Safe content is preserved
        assert "Starting build #123" in sanitized
        assert "NullPointerException at MyClass.java:42" in sanitized
        assert "Connection refused" in sanitized

        # Multiple patterns detected
        assert len(patterns) > 0


class TestSimpleSanitization:
    """Tests for the simple sanitization function."""

    def test_simple_sanitize_returns_string(self):
        """sanitize_log_simple returns just the sanitized string."""
        log = "password=secret123"
        result = sanitize_log_simple(log)

        assert isinstance(result, str)
        assert "secret123" not in result


class TestPatternNames:
    """Tests for pattern name retrieval."""

    def test_get_pattern_names_returns_list(self):
        """get_pattern_names returns a list of all pattern names."""
        names = get_pattern_names()

        assert isinstance(names, list)
        assert len(names) > 0
        assert "aws_access_key" in names
        assert "github_token" in names
        assert "password_assignment" in names
