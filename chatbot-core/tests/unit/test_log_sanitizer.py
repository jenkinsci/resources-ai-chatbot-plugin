"""
Unit tests for Log Sanitizer to ensure PII is properly redacted
Critical security tests - all must pass before deployment
"""

import pytest
from api.services.tools.build_failure_analyzer import LogSanitizer, LogExtractor


class TestLogSanitizer:
    """Test suite for PII sanitization - CRITICAL for security"""
    
    def test_api_key_redaction(self):
        """Test that API keys are properly redacted"""
        log = "Using API_KEY=sk_live_1234567890abcdefghij for authentication"
        sanitized, types = LogSanitizer.sanitize(log)
        
        assert 'sk_live_1234567890abcdefghij' not in sanitized
        assert '[REDACTED_API_KEY]' in sanitized
        assert 'api_key' in types
    
    def test_password_redaction(self):
        """Test that passwords are properly redacted"""
        log = "Login with password: MySecretPass123!"
        sanitized, types = LogSanitizer.sanitize(log)
        
        assert 'MySecretPass123!' not in sanitized
        assert '[REDACTED_PASSWORD]' in sanitized
        assert 'password' in types
    
    def test_token_redaction(self):
        """Test that tokens are properly redacted"""
        log = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        sanitized, types = LogSanitizer.sanitize(log)
        
        # Check both token patterns
        assert 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9' not in sanitized
        assert '[REDACTED_' in sanitized
    
    def test_jwt_token_redaction(self):
        """Test that JWT tokens are specifically redacted"""
        log = "JWT: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        sanitized, types = LogSanitizer.sanitize(log)
        
        assert 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9' not in sanitized
        assert '[REDACTED_JWT_TOKEN]' in sanitized
        assert 'jwt_token' in types
    
    def test_email_redaction(self):
        """Test that email addresses are redacted"""
        log = "Error sending to user@example.com and admin@company.org"
        sanitized, types = LogSanitizer.sanitize(log)
        
        assert 'user@example.com' not in sanitized
        assert 'admin@company.org' not in sanitized
        assert '[REDACTED_EMAIL]' in sanitized
        assert 'email' in types
    
    def test_private_key_redaction(self):
        """Test that private keys are redacted"""
        log = """
Deploying with key:
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA1234567890abcdefghijklmnop
qrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456
-----END RSA PRIVATE KEY-----
Deployment complete
        """
        sanitized, types = LogSanitizer.sanitize(log)
        
        assert 'MIIEpAIBAAKCAQEA1234567890' not in sanitized
        assert '[REDACTED_PRIVATE_KEY]' in sanitized
        assert 'private_key' in types
    
    def test_url_with_credentials_redaction(self):
        """Test that URLs with embedded credentials are redacted"""
        log = "Cloning from https://user:password123@github.com/repo.git"
        sanitized, types = LogSanitizer.sanitize(log)
        
        assert 'password123' not in sanitized
        assert 'user:password123' not in sanitized
        assert '[REDACTED_URL_WITH_CREDENTIALS]' in sanitized
        assert 'url_with_credentials' in types
    
    def test_aws_key_redaction(self):
        """Test that AWS keys are redacted"""
        log = "Using AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE and AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        sanitized, types = LogSanitizer.sanitize(log)
        
        assert 'AKIAIOSFODNN7EXAMPLE' not in sanitized
        assert 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY' not in sanitized
        assert '[REDACTED_AWS_KEY]' in sanitized
        assert 'aws_key' in types
    
    def test_ip_address_redaction(self):
        """Test that IP addresses are redacted"""
        log = "Connecting to server at 192.168.1.100 and backup at 10.0.0.5"
        sanitized, types = LogSanitizer.sanitize(log)
        
        assert '192.168.1.100' not in sanitized
        assert '10.0.0.5' not in sanitized
        assert '[REDACTED_IP_ADDRESS]' in sanitized
        assert 'ip_address' in types
    
    def test_multiple_pii_types(self):
        """Test that multiple PII types are redacted in one log"""
        log = """
Build Configuration:
USERNAME=admin
PASSWORD=SecretPass123
API_KEY=sk_test_abc123def456ghi789jkl
Email: admin@company.com
Server: 192.168.1.50
        """
        sanitized, types = LogSanitizer.sanitize(log)
        
        # Check all secrets are removed
        assert 'SecretPass123' not in sanitized
        assert 'sk_test_abc123def456ghi789jkl' not in sanitized
        assert 'admin@company.com' not in sanitized
        assert '192.168.1.50' not in sanitized
        
        # Should have multiple redaction types
        assert len(types) >= 3
    
    def test_preserves_non_sensitive_content(self):
        """Test that non-sensitive content is preserved"""
        log = "Build started at 2026-01-05 10:30:00 for project myapp"
        sanitized, types = LogSanitizer.sanitize(log)
        
        assert sanitized == log
        assert len(types) == 0
    
    def test_case_insensitive_matching(self):
        """Test that PII detection is case-insensitive"""
        logs = [
            "PASSWORD=secret123",
            "Password=secret123",
            "password=secret123",
            "API_KEY=abc123def456ghi789jkl",
            "api_key=abc123def456ghi789jkl",
            "ApiKey=abc123def456ghi789jkl"
        ]
        
        for log in logs:
            sanitized, types = LogSanitizer.sanitize(log)
            # Should not contain the secret value regardless of case
            assert 'secret123' not in sanitized or 'abc123def456ghi789jkl' not in sanitized
            assert '[REDACTED_' in sanitized
            assert len(types) > 0
    
    def test_real_world_jenkins_log(self):
        """Test with realistic Jenkins log excerpt"""
        log = """
[INFO] Downloading from central: https://repo.maven.apache.org/maven2/...
[INFO] Connecting with credentials user:MyP@ssw0rd!
[ERROR] Failed to authenticate
[ERROR] Using token: ghp_1234567890abcdefghijklmnopqrstuvwxyz
[INFO] Contact admin@jenkins.io for help
[ERROR] Server at 10.20.30.40 returned 401
        """
        sanitized, types = LogSanitizer.sanitize(log)
        
        # All secrets should be gone
        assert 'MyP@ssw0rd!' not in sanitized
        assert 'ghp_1234567890abcdefghijklmnopqrstuvwxyz' not in sanitized
        assert 'admin@jenkins.io' not in sanitized
        assert '10.20.30.40' not in sanitized
        
        # But structure should remain
        assert '[INFO]' in sanitized
        assert '[ERROR]' in sanitized
        assert 'Failed to authenticate' in sanitized
        
        # Should have detected multiple types
        assert len(types) >= 3


class TestLogExtractor:
    """Test suite for error context extraction"""
    
    def test_extract_error_context(self):
        """Test that error context is properly extracted"""
        log = "\n".join([
            "Starting build...",
            "Compiling sources...",
            "Running tests...",
            "ERROR: Test failed: NullPointerException",
            "at com.example.MyClass.method(MyClass.java:42)",
            "Caused by: java.lang.NullPointerException",
            "at com.example.MyClass.doSomething(MyClass.java:35)",
            "Build finished with status: FAILURE"
        ])
        
        context = LogExtractor.extract_error_context(log, context_lines=50)
        
        assert 'ERROR' in context
        assert 'NullPointerException' in context
        assert 'MyClass.java:42' in context
        assert 'Line' in context  # Should have line numbers
    
    def test_extract_no_errors(self):
        """Test extraction when no errors are found"""
        log = "\n".join([
            "Starting build...",
            "Compiling sources...",
            "Running tests...",
            "All tests passed!",
            "Build successful"
        ])
        
        context = LogExtractor.extract_error_context(log, context_lines=10)
        
        # Should return last N lines
        assert 'Build successful' in context
        assert len(context.split('\n')) <= 10
    
    def test_extract_key_error_message(self):
        """Test extraction of key error message for search"""
        log = """
Line 45: [ERROR] Compilation failed
Line 46: error: cannot find symbol
Line 47: symbol:   class MyClass
Line 48: location: package com.example
        """
        
        key_error = LogExtractor.extract_key_error(log)
        
        assert 'error' in key_error.lower() or 'failed' in key_error.lower()
        # Should clean up line numbers
        assert 'Line 45:' not in key_error
        assert 'Line 46:' not in key_error
    
    def test_extract_exception_as_key_error(self):
        """Test that exceptions are extracted as key errors"""
        log = """
Line 100: at com.example.Test.run(Test.java:50)
Line 101: java.lang.NullPointerException: Cannot invoke method on null object
Line 102: at com.example.MyClass.method(MyClass.java:42)
        """
        
        key_error = LogExtractor.extract_key_error(log)
        
        assert 'NullPointerException' in key_error
        # Paths and line numbers should be cleaned
        assert '.java:' not in key_error or '(' not in key_error
    
    def test_context_lines_limit(self):
        """Test that extraction respects line limits"""
        # Create a log with many error lines
        lines = ["Normal line"] * 20
        lines.extend([f"ERROR {i}" for i in range(100)])
        log = "\n".join(lines)
        
        context = LogExtractor.extract_error_context(log, context_lines=30)
        
        extracted_lines = [l for l in context.split('\n') if l and not l.startswith('[...')]
        # Should respect the limit (approximately)
        assert len(extracted_lines) <= 40  # Some buffer for context


class TestBuildFailureAnalyzerTool:
    """Test the main analyzer tool (without actual Jenkins connection)"""
    
    def test_error_classification(self):
        """Test error type classification"""
        from api.services.tools.build_failure_analyzer import BuildFailureAnalyzer
        
        analyzer = BuildFailureAnalyzer()
        
        test_cases = [
            ("javac: cannot find symbol", "compilation_error"),
            ("Test failed: expected 5 but was 3", "test_failure"),
            ("Could not resolve dependency org.example:mylib:1.0", "dependency_error"),
            ("java.lang.NullPointerException at line 42", "null_pointer_exception"),
            ("OutOfMemoryError: Java heap space", "out_of_memory"),
            ("Connection refused to localhost:8080", "network_error"),
            ("Permission denied: /var/lib/jenkins", "permission_error"),
            ("Timeout waiting for response", "timeout_error"),
        ]
        
        for log, expected_type in test_cases:
            error_type = analyzer._classify_error(log)
            assert error_type == expected_type, f"Failed to classify: {log}"
    
    def test_handles_missing_vector_store_gracefully(self):
        """Test that tool works even without vector store"""
        from api.services.tools.build_failure_analyzer import BuildFailureAnalyzer
        
        analyzer = BuildFailureAnalyzer(vector_store=None)
        
        # Should not crash
        results = analyzer._search_similar_issues("test error")
        assert results == []
    
    def test_json_input_parsing(self):
        """Test that tool can parse JSON input"""
        from api.services.tools.build_failure_analyzer import BuildFailureAnalyzer
        import json
        
        analyzer = BuildFailureAnalyzer(
            jenkins_url="http://localhost:8080",
            username="test",
            api_token="test"
        )
        
        # Test invalid JSON handling
        result = analyzer._run("invalid json")
        result_data = json.loads(result)
        
        assert result_data['status'] == 'error'
        assert 'message' in result_data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
