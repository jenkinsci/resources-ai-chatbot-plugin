"""Module for sanitizing logs by redacting sensitive information."""

import re


SECRET_NAME_PATTERN = (
    r"TOKEN|SECRET|PASSWORD|PASSWD|PSW|PASSPHRASE|"
    r"API[-_]?KEY|PRIVATE[-_]?KEY|CREDENTIALS?|CREDS"
)

# Private key blocks can appear in full or be truncated near the end of logs.
PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"
    r".*?"
    r"(?:-----END [A-Z0-9 ]*PRIVATE KEY-----|\Z)",
    re.DOTALL,
)

# Env, JSON, and config-style values such as TOKEN=abc or "api_key": "abc".
SECRET_ASSIGNMENT_PATTERN = re.compile(
    rf"""
    (?P<prefix>
        ["']?
        [A-Za-z0-9_.-]*
        (?:{SECRET_NAME_PATTERN})
        (?![A-Za-z0-9_-])
        ["']?
        \s*[:=]\s*
    )
    (?:
        "(?P<double_value>(?:\\.|[^"\\\r\n])*)"
        |
        '(?P<single_value>(?:\\.|[^'\\\r\n])*)'
        |
        (?P<bare_value>[^\s,;&\]\['\"]+)
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

REDACTION_PATTERNS = (
    # HTTP auth headers, API-key headers, Jenkins crumbs, and cookies.
    (
        re.compile(
            r"(?im)(\b(?:Authorization|Proxy-Authorization|X-API-Key|"
            r"X-Auth-Token|Private-Token|Jenkins-Crumb|Cookie|Set-Cookie)"
            r"\s*:\s*)[^'\"\r\n]+"
        ),
        r"\1[REDACTED]",
    ),
    # Docker login password flags; --password-stdin is intentionally not matched.
    (
        re.compile(
            r"(?i)(\bdocker\s+login\b[^\r\n]*?"
            r"\s(?:-p|--password)(?:\s+|=))"
            r"([^\s'\";]+)"
        ),
        r"\1[REDACTED]",
    ),
    # Passwords embedded in URLs, for example https://user:pass@example.com.
    (
        re.compile(r"(?i)(\b[a-z][a-z0-9+.-]*://[^/\s:@]+:)([^@\s/]+)(@)"),
        r"\1[REDACTED]\3",
    ),
    # Sensitive query-string values while preserving surrounding quotes and params.
    (
        re.compile(
            r"(?i)([?&](?:token|access_token|auth_token|api_key|"
            r"client_secret|password)=)[^&#\s'\"]+"
        ),
        r"\1[REDACTED]",
    ),
    # AWS access key IDs.
    (
        re.compile(r"(?<![A-Z0-9])(?:AKIA|ASIA)[0-9A-Z]{16}(?![A-Z0-9])"),
        "[REDACTED_AWS_KEY]",
    ),
    # GitHub classic and fine-grained token formats.
    (
        re.compile(r"\b(?:github_pat_[A-Za-z0-9_]+|gh[a-z]_[A-Za-z0-9]{30,})\b"),
        "[REDACTED_GITHUB_TOKEN]",
    ),
    # OpenAI-style and Groq-style API keys.
    (
        re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|gsk_[A-Za-z0-9_-]{20,})\b"),
        "[REDACTED_API_KEY]",
    ),
    # Compact JWT-like tokens.
    (
        re.compile(r"\beyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]*){2,4}\b"),
        "[REDACTED_JWT]",
    ),
)


def _redact_assignment(match: re.Match[str]) -> str:
    """
    Redact a secret assignment value while preserving simple quote style.

    Args:
        match (re.Match[str]): Regex match for a secret assignment.

    Returns:
        str: Assignment with the value redacted.
    """
    prefix = match.group("prefix")
    if match.group("double_value") is not None:
        return f'{prefix}"[REDACTED]"'
    if match.group("single_value") is not None:
        return f"{prefix}'[REDACTED]'"
    return f"{prefix}[REDACTED]"


def sanitize_logs(log_text: str) -> str:
    """
    Scans the input text for common secret patterns and redacts them.

    Args:
        log_text (str): Raw Jenkins log text.

    Returns:
        str: Sanitized log text.
    """
    if not log_text:
        return ""

    sanitized_text = PRIVATE_KEY_PATTERN.sub("[REDACTED_PRIVATE_KEY]", log_text)
    sanitized_text = SECRET_ASSIGNMENT_PATTERN.sub(
        _redact_assignment,
        sanitized_text,
    )

    for pattern, replacement in REDACTION_PATTERNS:
        sanitized_text = pattern.sub(replacement, sanitized_text)

    return sanitized_text
