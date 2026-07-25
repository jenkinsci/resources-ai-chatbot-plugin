"""Module for sanitizing Jenkins logs before sending them to an LLM."""

import re


SECRET_NAME_PATTERN = (
    r"TOKEN|SECRET|PASSWORD|PASSWD|PSW|API[-_]?KEY|"
    r"ACCESS[-_]?KEY|SECRET[-_]?KEY|PRIVATE[-_]?KEY|CREDENTIALS?|CREDS"
)
SECRET_NAME_RE = re.compile(
    rf"(?:^|[_\-.])(?:{SECRET_NAME_PATTERN})(?:$|[_\-.])",
    re.IGNORECASE,
)

# Private key blocks may be complete or truncated at the end of a console log.
PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"
    r".*?"
    r"(?:-----END [A-Z0-9 ]*PRIVATE KEY-----|\Z)",
    re.DOTALL,
)

# Assignments in shell, Jenkins echo, JSON-like, and config-like output.
SECRET_ASSIGNMENT_PATTERN = re.compile(
    r"""
    (?P<prefix>
        (?:^|[\s{,])
        (?:\+\s*)?
        (?:export\s+)?
        (?:\d+:\s*)?
        (?P<name_quote>["']?)
        (?P<name>[A-Za-z_][A-Za-z0-9_.-]*)
        (?P=name_quote)
        \s*[:=]\s*
    )
    (?P<value>
        "(?:\\.|[^"\\\r\n])*"
        |
        '(?:\\.|[^'\\\r\n])*'
        |
        \${[^}\r\n]*}
        |
        [^\r\n,;&}\]\[]+
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

REDACTION_PATTERNS = (
    # HTTP authentication, API key headers, Jenkins crumbs, and cookies.
    (
        re.compile(
            r"(?im)(\b(?:Authorization|Proxy-Authorization|X-API-Key|"
            r"X-Auth-Token|Private-Token|Jenkins-Crumb|Cookie|Set-Cookie)"
            r"\s*:\s*)[^'\"\r\n]+"
        ),
        r"\1[REDACTED]",
    ),
    # Passwords embedded in URLs, for example https://user:pass@example.com.
    (
        re.compile(r"(?i)(\b[a-z][a-z0-9+.-]*://[^/\s:@]+:)([^@\s/]+)(@)"),
        r"\1[REDACTED]\3",
    ),
    # Sensitive query-string values while preserving surrounding params.
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


def _normalize_assignment_name(name: str) -> str:
    """
    Normalize assignment names before matching secret words.

    Args:
        name (str): Assignment key from a Jenkins log line.

    Returns:
        str: Name with camel-case boundaries converted to underscores.
    """
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)


def _is_secret_assignment_name(name: str) -> bool:
    """
    Check whether an assignment name looks secret-related.

    Args:
        name (str): Assignment key from a Jenkins log line.

    Returns:
        bool: True when the assignment should be redacted.
    """
    return bool(SECRET_NAME_RE.search(_normalize_assignment_name(name)))


def _redact_assignment(match: re.Match[str]) -> str:
    """
    Redact a secret assignment while preserving simple quote style.

    Args:
        match (re.Match[str]): Regex match for a secret assignment.

    Returns:
        str: Assignment with its value redacted.
    """
    prefix = match.group("prefix")
    value = match.group("value")
    if not _is_secret_assignment_name(match.group("name")):
        return match.group(0)

    if value.startswith('"') and value.endswith('"'):
        return f'{prefix}"[REDACTED]"'
    if value.startswith("'") and value.endswith("'"):
        return f"{prefix}'[REDACTED]'"

    return f"{prefix}[REDACTED]"


def sanitize_logs(log_text: str) -> str:
    """
    Redact common secrets from Jenkins console log text.

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
