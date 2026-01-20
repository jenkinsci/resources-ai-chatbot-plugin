"""
PII Sanitization Service for Build Log Analysis.

Automatically detects and masks sensitive information (secrets, API keys,
passwords, tokens, credentials) before sending data to any LLM.
"""

import re
from typing import List, Tuple, Pattern
from dataclasses import dataclass


@dataclass
class SanitizationPattern:
    """Represents a pattern for detecting sensitive information."""
    name: str
    pattern: Pattern
    replacement: str


# Compiled regex patterns for various secret types
SANITIZATION_PATTERNS: List[SanitizationPattern] = [
    # AWS Access Key IDs (20 alphanumeric starting with AKIA, ABIA, ACCA, ASIA)
    SanitizationPattern(
        name="aws_access_key",
        pattern=re.compile(r'\b(A[KBS]IA[A-Z0-9]{16})\b'),
        replacement="[AWS_KEY_REDACTED]"
    ),
    # AWS Secret Access Keys (40 alphanumeric, typically after AWS_SECRET)
    SanitizationPattern(
        name="aws_secret_key",
        pattern=re.compile(
            r'(?:AWS_SECRET_ACCESS_KEY|aws_secret_access_key|SecretAccessKey)'
            r'[\s]*[=:]\s*["\']?([A-Za-z0-9/+=]{40})["\']?',
            re.IGNORECASE
        ),
        replacement="[AWS_SECRET_REDACTED]"
    ),
    # GitHub Personal Access Tokens (ghp_, gho_, ghu_, ghs_, ghr_)
    SanitizationPattern(
        name="github_token",
        pattern=re.compile(r'\b(gh[pousr]_[A-Za-z0-9_]{36,255})\b'),
        replacement="[GITHUB_TOKEN_REDACTED]"
    ),
    # Generic API Keys (various common patterns)
    SanitizationPattern(
        name="generic_api_key",
        pattern=re.compile(
            r'(?:api[_-]?key|apikey|api_token|access_token)'
            r'[\s]*[=:]\s*["\']?([A-Za-z0-9_\-]{20,})["\']?',
            re.IGNORECASE
        ),
        replacement="[API_KEY_REDACTED]"
    ),
    # Bearer Tokens
    SanitizationPattern(
        name="bearer_token",
        pattern=re.compile(
            r'Bearer\s+([A-Za-z0-9_\-\.]+)',
            re.IGNORECASE
        ),
        replacement="Bearer [TOKEN_REDACTED]"
    ),
    # JWT Tokens (three base64 parts separated by dots)
    SanitizationPattern(
        name="jwt_token",
        pattern=re.compile(
            r'\b(eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*)\b'
        ),
        replacement="[JWT_REDACTED]"
    ),
    # Password in URLs (user:password@host patterns)
    SanitizationPattern(
        name="url_password",
        pattern=re.compile(
            r'://([^:]+):([^@]+)@',
            re.IGNORECASE
        ),
        replacement="://[USER_REDACTED]:[PASSWORD_REDACTED]@"
    ),
    # Password assignments (password = value, passwd: value, etc.)
    SanitizationPattern(
        name="password_assignment",
        pattern=re.compile(
            r'(?:password|passwd|pwd|secret|credential|auth_token)'
            r'[\s]*[=:]\s*["\']?([^\s"\']{4,})["\']?',
            re.IGNORECASE
        ),
        replacement=r"\g<0>".replace(r"\g<0>", "[PASSWORD_REDACTED]")
    ),
    # Private Keys (RSA, SSH, etc.)
    SanitizationPattern(
        name="private_key",
        pattern=re.compile(
            r'-----BEGIN\s+(?:RSA\s+)?(?:PRIVATE|ENCRYPTED)\s+KEY-----'
            r'[\s\S]*?'
            r'-----END\s+(?:RSA\s+)?(?:PRIVATE|ENCRYPTED)\s+KEY-----',
            re.IGNORECASE
        ),
        replacement="[PRIVATE_KEY_REDACTED]"
    ),
    # SSH Private Keys (DSA, EC, OPENSSH)
    SanitizationPattern(
        name="ssh_key",
        pattern=re.compile(
            r'-----BEGIN\s+(?:DSA|EC|OPENSSH)\s+PRIVATE\s+KEY-----'
            r'[\s\S]*?'
            r'-----END\s+(?:DSA|EC|OPENSSH)\s+PRIVATE\s+KEY-----',
            re.IGNORECASE
        ),
        replacement="[SSH_KEY_REDACTED]"
    ),
    # Jenkins API Token patterns
    SanitizationPattern(
        name="jenkins_token",
        pattern=re.compile(
            r'(?:JENKINS_API_TOKEN|jenkins_token|J_API_TOKEN)'
            r'[\s]*[=:]\s*["\']?([A-Za-z0-9]{32,})["\']?',
            re.IGNORECASE
        ),
        replacement="[JENKINS_TOKEN_REDACTED]"
    ),
    # Base64 encoded credentials (common in CI/CD)
    SanitizationPattern(
        name="base64_credentials",
        pattern=re.compile(
            r'(?:basic|auth|credentials?|authorization)'
            r'[\s]*[=:]\s*["\']?([A-Za-z0-9+/]{40,}={0,2})["\']?',
            re.IGNORECASE
        ),
        replacement="[BASE64_CREDENTIALS_REDACTED]"
    ),
    # Slack Tokens (xoxb-, xoxp-, xoxa-, xoxr-)
    SanitizationPattern(
        name="slack_token",
        pattern=re.compile(r'\b(xox[bpar]-[A-Za-z0-9\-]+)\b'),
        replacement="[SLACK_TOKEN_REDACTED]"
    ),
    # NPM Tokens
    SanitizationPattern(
        name="npm_token",
        pattern=re.compile(r'\b(npm_[A-Za-z0-9]{36})\b'),
        replacement="[NPM_TOKEN_REDACTED]"
    ),
    # Docker Registry Credentials
    SanitizationPattern(
        name="docker_auth",
        pattern=re.compile(
            r'"auth"\s*:\s*"([A-Za-z0-9+/=]{20,})"'
        ),
        replacement='"auth": "[DOCKER_AUTH_REDACTED]"'
    ),
    # Generic high-entropy secrets (32+ hex chars that look like hashes/tokens)
    SanitizationPattern(
        name="hex_secret",
        pattern=re.compile(
            r'(?:secret|token|key|hash)[\s]*[=:]\s*["\']?([a-fA-F0-9]{32,})["\']?',
            re.IGNORECASE
        ),
        replacement="[HEX_SECRET_REDACTED]"
    ),
    # Environment variable exports with secrets
    SanitizationPattern(
        name="export_secret",
        pattern=re.compile(
            r'export\s+(?:API_KEY|SECRET|TOKEN|PASSWORD|CREDENTIALS?|AUTH)'
            r'[A-Z_0-9]*\s*=\s*["\']?([^\s"\']+)["\']?',
            re.IGNORECASE
        ),
        replacement="export [VAR_REDACTED]=[VALUE_REDACTED]"
    ),
]


def sanitize_log(log_content: str) -> Tuple[str, List[str]]:
    """
    Sanitize a build log by replacing all detected sensitive information.

    Args:
        log_content: The raw build log content.

    Returns:
        Tuple of (sanitized_log, list_of_detected_pattern_names)
    """
    sanitized = log_content
    detected_patterns: List[str] = []

    for pattern_def in SANITIZATION_PATTERNS:
        if pattern_def.pattern.search(sanitized):
            detected_patterns.append(pattern_def.name)
            sanitized = pattern_def.pattern.sub(
                pattern_def.replacement,
                sanitized
            )

    return sanitized, detected_patterns


def sanitize_log_simple(log_content: str) -> str:
    """
    Simple version that just returns the sanitized log.

    Args:
        log_content: The raw build log content.

    Returns:
        Sanitized log content with all secrets masked.
    """
    sanitized, _ = sanitize_log(log_content)
    return sanitized


def get_pattern_names() -> List[str]:
    """
    Get list of all pattern names that we detect.

    Returns:
        List of pattern names.
    """
    return [p.name for p in SANITIZATION_PATTERNS]
