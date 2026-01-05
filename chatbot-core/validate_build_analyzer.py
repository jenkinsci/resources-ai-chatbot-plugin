"""
Quick validation script for build failure analyzer
Tests the core functionality without requiring full pytest setup
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.services.tools.build_failure_analyzer import LogSanitizer, LogExtractor


def test_log_sanitizer():
    """Test PII sanitization"""
    print("Testing LogSanitizer...")

    # Test 1: API Key redaction
    log1 = "Using API_KEY=sk_live_1234567890abcdefghij for authentication"
    sanitized1, types1 = LogSanitizer.sanitize(log1)
    assert 'sk_live_1234567890abcdefghij' not in sanitized1, "âŒ API key not redacted!"
    assert '[REDACTED_API_KEY]' in sanitized1, "âŒ Redaction marker missing!"
    print("âœ… API key redaction works")

    # Test 2: Password redaction
    log2 = "Login with password: MySecretPass123!"
    sanitized2, types2 = LogSanitizer.sanitize(log2)
    assert 'MySecretPass123!' not in sanitized2, "âŒ Password not redacted!"
    assert '[REDACTED_PASSWORD]' in sanitized2, "âŒ Redaction marker missing!"
    print("âœ… Password redaction works")

    # Test 3: Email redaction
    log3 = "Error sending to user@example.com"
    sanitized3, types3 = LogSanitizer.sanitize(log3)
    assert 'user@example.com' not in sanitized3, "âŒ Email not redacted!"
    assert '[REDACTED_EMAIL]' in sanitized3, "âŒ Redaction marker missing!"
    print("âœ… Email redaction works")

    # Test 4: Multiple PII types
    log4 = """
    Build Configuration:
    PASSWORD=SecretPass123
    API_KEY=sk_test_abc123def456ghi789jkl
    Email: admin@company.com
    Server: 192.168.1.50
    """
    sanitized4, types4 = LogSanitizer.sanitize(log4)
    assert 'SecretPass123' not in sanitized4, "âŒ Password in multi-PII not redacted!"
    assert 'sk_test_abc123def456ghi789jkl' not in sanitized4, "âŒ API key in multi-PII not redacted!"
    assert 'admin@company.com' not in sanitized4, "âŒ Email in multi-PII not redacted!"
    assert '192.168.1.50' not in sanitized4, "âŒ IP in multi-PII not redacted!"
    assert len(types4) >= 3, "âŒ Not all PII types detected!"
    print("âœ… Multiple PII types redaction works")

    # Test 5: JWT token redaction
    log5 = "JWT: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc123"
    sanitized5, types5 = LogSanitizer.sanitize(log5)
    assert 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9' not in sanitized5, "âŒ JWT not redacted!"
    print("âœ… JWT token redaction works")

    # Test 6: Private key redaction
    log6 = """
    -----BEGIN RSA PRIVATE KEY-----
    MIIEpAIBAAKCAQEA1234567890
    -----END RSA PRIVATE KEY-----
    """
    sanitized6, types6 = LogSanitizer.sanitize(log6)
    assert 'MIIEpAIBAAKCAQEA1234567890' not in sanitized6, "âŒ Private key not redacted!"
    print("âœ… Private key redaction works")

    # Test 7: URL with credentials
    log7 = "Cloning from https://user:password123@github.com/repo.git"
    sanitized7, types7 = LogSanitizer.sanitize(log7)
    assert 'password123' not in sanitized7, "âŒ URL credential not redacted!"
    print("âœ… URL credential redaction works")

    # Test 8: Non-sensitive content preserved
    log8 = "Build started at 2026-01-05 10:30:00 for project myapp"
    sanitized8, types8 = LogSanitizer.sanitize(log8)
    assert sanitized8 == log8, "âŒ Non-sensitive content was modified!"
    assert len(types8) == 0, "âŒ False positive detected!"
    print("âœ… Non-sensitive content preservation works")

    print("\nðŸŽ‰ All LogSanitizer tests passed!\n")


def test_log_extractor():
    """Test error context extraction"""
    print("Testing LogExtractor...")

    # Test 1: Extract error context
    log1 = "\n".join([
        "Starting build...",
        "Compiling sources...",
        "Running tests...",
        "ERROR: Test failed: NullPointerException",
        "at com.example.MyClass.method(MyClass.java:42)",
        "Caused by: java.lang.NullPointerException",
        "Build finished with status: FAILURE"
    ])
    context1 = LogExtractor.extract_error_context(log1, context_lines=50)
    assert 'ERROR' in context1, "âŒ ERROR marker not found!"
    assert 'NullPointerException' in context1, "âŒ Exception not found!"
    assert 'Line' in context1, "âŒ Line numbers missing!"
    print("âœ… Error context extraction works")

    # Test 2: Extract key error message
    log2 = """
Line 45: [ERROR] Compilation failed
Line 46: error: cannot find symbol
Line 47: symbol:   class MyClass
    """
    key_error = LogExtractor.extract_key_error(log2)
    assert 'error' in key_error.lower() or 'failed' in key_error.lower(), "âŒ Key error not extracted!"
    print("âœ… Key error extraction works")

    # Test 3: Handle logs with no errors
    log3 = "\n".join([
        "Starting build...",
        "All tests passed!",
        "Build successful"
    ])
    context3 = LogExtractor.extract_error_context(log3, context_lines=10)
    assert 'Build successful' in context3, "âŒ Fallback to last lines failed!"
    print("âœ… No-error log handling works")

    print("\nðŸŽ‰ All LogExtractor tests passed!\n")


def test_error_classification():
    """Test error type classification"""
    print("Testing Error Classification...")

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
        assert error_type == expected_type, f"âŒ Failed to classify: {log} (got {error_type}, expected {expected_type})"
        print(f"âœ… Classified '{expected_type}' correctly")

    print("\nðŸŽ‰ All Error Classification tests passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Build Failure Analyzer - Validation Tests")
    print("=" * 60)
    print()

    try:
        test_log_sanitizer()
        test_log_extractor()
        test_error_classification()

        print("=" * 60)
        print("âœ… ALL TESTS PASSED - Implementation is working correctly!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Set Jenkins credentials in config.yml or environment variables")
        print("2. Start the FastAPI server: uvicorn api.main:app --reload")
        print("3. Test the endpoint: POST /api/chatbot/build-analysis/analyze")
        print()

    except AssertionError as e:
        print(f"\nâŒ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nâŒ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
