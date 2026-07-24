"""Extract small error sections from Jenkins console logs."""

import re


DEFAULT_CONTEXT_LINES = 10
DEFAULT_CONTEXT_AFTER_LINES = 5

ERROR_PATTERN = re.compile(
    r"""
    \[(?:ERROR|FATAL)\]
    |
    \bFATAL:
    |
    \bBUILD\s+FAILURE\b
    |
    \bFAILURE:\s+Build\s+failed\b
    """,
    flags=re.IGNORECASE | re.VERBOSE,
)
WRAPPER_ERROR_PATTERN = re.compile(
    r"\bERROR:\s+script\s+returned\s+exit\s+code\b",
    flags=re.IGNORECASE,
)


def extract_error_context(
    log_text: str,
    context_lines: int = DEFAULT_CONTEXT_LINES,
    context_after: int = DEFAULT_CONTEXT_AFTER_LINES,
) -> str:
    """
    Extract each meaningful error with nearby Jenkins log lines.

    Args:
        log_text (str): Raw Jenkins console log.
        context_lines (int): Number of lines to include before each error.
        context_after (int): Number of lines to include after each error.

    Returns:
        str: Selected log sections in their original order.
    """
    if not log_text:
        return ""

    lines = log_text.splitlines()
    selected_indexes: set[int] = set()
    error_indexes = [
        index
        for index, line in enumerate(lines)
        if ERROR_PATTERN.search(line)
    ]
    if not error_indexes:
        error_indexes = [
            index
            for index, line in enumerate(lines)
            if WRAPPER_ERROR_PATTERN.search(line)
        ]

    for index in error_indexes:
        start = max(0, index - max(0, context_lines))
        end = min(len(lines), index + max(0, context_after) + 1)
        selected_indexes.update(range(start, end))

    if any(ERROR_PATTERN.search(line) for line in lines):
        selected_indexes = {
            index
            for index in selected_indexes
            if not WRAPPER_ERROR_PATTERN.search(lines[index])
        }

    if not selected_indexes:
        return "\n".join(lines[-context_lines:])

    return render_selected_lines(lines, sorted(selected_indexes))


def extract_relevant_log_lines(
    log_text: str,
    context_before: int = DEFAULT_CONTEXT_LINES,
    context_after: int = DEFAULT_CONTEXT_AFTER_LINES,
    tail_lines: int = DEFAULT_CONTEXT_LINES,
    max_chars: int = 0,
) -> str:
    """
    Keep compatibility with the existing service call.

    Args:
        log_text (str): Raw Jenkins console log.
        context_before (int): Number of lines before each error.
        context_after (int): Number of lines after each error.
        tail_lines (int): Number of fallback tail lines.
        max_chars (int): Unused; kept for compatibility.

    Returns:
        str: Selected error context.
    """
    del max_chars

    if not log_text:
        return ""

    selected = extract_error_context(log_text, context_before, context_after)
    if selected:
        return selected

    return "\n".join(log_text.splitlines()[-tail_lines:])


def render_selected_lines(lines: list[str], selected_indexes: list[int]) -> str:
    """
    Render selected lines with original line numbers and omission markers.

    Args:
        lines (list[str]): Full log lines.
        selected_indexes (list[int]): Selected zero-based line indexes.

    Returns:
        str: Rendered log sections.
    """
    output: list[str] = []
    previous_index: int | None = None

    for index in selected_indexes:
        if previous_index is not None and index > previous_index + 1:
            output.append("[... unrelated log lines omitted ...]")

        output.append(f"{index + 1}: {lines[index]}")
        previous_index = index

    return "\n".join(output)
