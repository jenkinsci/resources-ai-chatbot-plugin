"""Module for sanitizing logs by redacting sensitive information."""
import re

def sanitize_logs(log_text: str) -> str:
    """
    Scans the input text for common secret patterns (API keys, passwords, tokens)
    and replaces them with [REDACTED].
    """
    patterns = [
        # Generic "password=" or "pwd=" patterns (case insensitive)
        (
            r'(?i)(password|passwd|pwd|secret|access_token|api_key|client_secret)'
            r'\s*[:=]\s*([^\s]+)',
            r'\1=[REDACTED]'
        ),

        # AWS Access Key ID (AKI...)
        (r'(?<![A-Z0-9])[A-Z0-9]{20}(?![A-Z0-9])', r'[REDACTED_AWS_KEY]'),

        # Generic Bearer Token
        (r'(?i)(Bearer)\s+[a-zA-Z0-9\-\._~+/]+=*', r'\1 [REDACTED_TOKEN]'),

        # GitHub Tokens (ghp_...)
        (r'ghp_[a-zA-Z0-9]{36}', r'[REDACTED_GITHUB_TOKEN]'),

        # Private Key Blocks
        (r'-----BEGIN [A-Z]+ PRIVATE KEY-----.*?-----END [A-Z]+ PRIVATE KEY-----',
         r'[REDACTED_PRIVATE_KEY]'
         ),

        # Docker Login Flags (-p password)
        (r'(docker\s+login.*?-p\s+)([^\s]+)', r'\1[REDACTED]')
    ]

    sanitized_text = log_text
    for pattern, replacement in patterns:
        sanitized_text = re.sub(pattern, replacement, sanitized_text, flags=re.DOTALL)

    return sanitized_text
