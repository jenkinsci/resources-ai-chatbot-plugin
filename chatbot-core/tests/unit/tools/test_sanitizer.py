"""Focused tests for Jenkins log sanitization."""

import pytest

from api.tools.sanitizer import sanitize_logs


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("TOKEN=abc123", "TOKEN=[REDACTED]"),
        ("export TOKEN=abc123", "export TOKEN=[REDACTED]"),
        ("+ TOKEN=abc123", "+ TOKEN=[REDACTED]"),
        ("257: TOKEN=abc123", "257: TOKEN=[REDACTED]"),
        ("clientSecret=abc123", "clientSecret=[REDACTED]"),
        ("accessToken=abc123", "accessToken=[REDACTED]"),
        ("AWS_SECRET_ACCESS_KEY=fake-secret", "AWS_SECRET_ACCESS_KEY=[REDACTED]"),
        ("PASSWORD=my secret password", "PASSWORD=[REDACTED]"),
        ('TOKEN="abc123"', 'TOKEN="[REDACTED]"'),
        ("PASSWORD='abc123'", "PASSWORD='[REDACTED]'"),
        ('"api_key": "abc", "status": "failed"', '"api_key": "[REDACTED]", "status": "failed"'),
        (
            '"api_key": "abc", "client_secret": "def", "status": "failed"',
            '"api_key": "[REDACTED]", "client_secret": "[REDACTED]", '
            '"status": "failed"',
        ),
    ],
)
def test_redacts_secret_assignments(raw, expected):
    """Redact assignment-shaped secrets while preserving surrounding syntax."""
    assert sanitize_logs(raw) == expected


def test_redacts_authentication_headers():
    """Redact values from common authentication headers."""
    assert sanitize_logs("Authorization: Bearer secret-token") == (
        "Authorization: [REDACTED]"
    )
    assert sanitize_logs("X-API-Key: secret-token") == "X-API-Key: [REDACTED]"
    assert sanitize_logs("Cookie: session=fake-cookie") == "Cookie: [REDACTED]"


def test_redacts_url_credentials():
    """Redact passwords embedded in HTTP and database URLs."""
    assert sanitize_logs("https://user:password@example.com/repository") == (
        "https://user:[REDACTED]@example.com/repository"
    )
    assert sanitize_logs("mongodb://user:password@database.example.com/app") == (
        "mongodb://user:[REDACTED]@database.example.com/app"
    )


def test_redacts_secret_query_parameters():
    """Redact secret query values without removing other parameters."""
    assert sanitize_logs("https://example.com/api?token=secret&debug=true") == (
        "https://example.com/api?token=[REDACTED]&debug=true"
    )
    assert sanitize_logs('curl "https://example.com?api_key=secret"') == (
        'curl "https://example.com?api_key=[REDACTED]"'
    )
    assert sanitize_logs("https://example.com/login?password=secret") == (
        "https://example.com/login?password=[REDACTED]"
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("AKIAIOSFODNN7EXAMPLE", "[REDACTED_AWS_KEY]"),
        ("ASIAIOSFODNN7EXAMPLE", "[REDACTED_AWS_KEY]"),
        (
            "ghp_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6",
            "[REDACTED_GITHUB_TOKEN]",
        ),
        (
            "github_pat_abcdefghijklmnopqrstuvwxyz1234567890",
            "[REDACTED_GITHUB_TOKEN]",
        ),
        ("sk-abcdefghijklmnopqrstuvwxyz123456", "[REDACTED_API_KEY]"),
        ("gsk_abcdefghijklmnopqrstuvwxyz123456", "[REDACTED_API_KEY]"),
        ("sk-proj-abcdefghijklmnopqrstuvwxyz123456", "[REDACTED_API_KEY]"),
        (
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.sig",
            "[REDACTED_JWT]",
        ),
    ],
)
def test_redacts_known_token_formats(raw, expected):
    """Redact common raw AWS, provider, GitHub, and JWT tokens."""
    assert sanitize_logs(raw) == expected


def test_redacts_complete_private_key_block():
    """Replace a complete private-key block with one marker."""
    raw = "\n".join(
        [
            "before",
            "-----BEGIN RSA PRIVATE KEY-----",
            "key material",
            "-----END RSA PRIVATE KEY-----",
            "after",
        ]
    )

    assert sanitize_logs(raw) == "before\n[REDACTED_PRIVATE_KEY]\nafter"


def test_redacts_truncated_private_key_block():
    """Replace a private-key block even when its closing marker is missing."""
    raw = "before\n-----BEGIN PRIVATE KEY-----\ntruncated key"

    assert sanitize_logs(raw) == "before\n[REDACTED_PRIVATE_KEY]"


def test_preserves_normal_non_secret_log_lines():
    """Leave ordinary diagnostic lines unchanged."""
    raw = "\n".join(
        ["status=failed", "HTTP_STATUS=401", "BUILD_NUMBER=123", "[ERROR] failed"]
    )

    assert sanitize_logs(raw) == raw


def test_is_idempotent():
    """Keep the output unchanged when sanitization is applied twice."""
    raw = "\n".join(
        [
            "TOKEN=abc123",
            "Authorization: Bearer secret-token",
            "https://user:password@example.com/repository",
        ]
    )
    sanitized = sanitize_logs(raw)

    assert sanitize_logs(sanitized) == sanitized
