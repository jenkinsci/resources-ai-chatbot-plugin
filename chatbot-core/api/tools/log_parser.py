"""Extract small error sections from Jenkins console logs."""

import re


DEFAULT_CONTEXT_BEFORE = 10
DEFAULT_CONTEXT_AFTER = 5
DEFAULT_TAIL_LINES = 10

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
    re.IGNORECASE | re.VERBOSE,
)
WRAPPER_ERROR_PATTERN = re.compile(
    r"\bERROR:\s+script\s+returned\s+exit\s+code\b",
    re.IGNORECASE,
)
FAILURE_FOOTER_PATTERN = re.compile(
    r"^\s*Finished:\s+FAILURE\s*$",
    re.IGNORECASE,
)


def extract_relevant_log_lines(
    log_text: str,
    context_before: int = DEFAULT_CONTEXT_BEFORE,
    context_after: int = DEFAULT_CONTEXT_AFTER,
    tail_lines: int = DEFAULT_TAIL_LINES,
    max_chars: int = 0,
) -> str:
    """
    Extract Jenkins error sections with nearby log lines.

    Args:
        log_text (str): Raw Jenkins console log.
        context_before (int): Lines included before each error.
        context_after (int): Lines included after each error.
        tail_lines (int): Lines returned when no error is found.
        max_chars (int): Unused; retained for compatibility.

    Returns:
        str: Extracted error sections or final log lines.
    """
    del max_chars

    if not log_text:
        return ""

    lines = log_text.splitlines()
    error_indexes = _find_error_indexes(lines)
    if not error_indexes:
        tail = max(0, tail_lines)
        return "\n".join(lines[-tail:]) if tail else ""

    before = max(0, context_before)
    after = max(0, context_after)
    selected_indexes: set[int] = set()

    for index in error_indexes:
        start = max(0, index - before)
        end = min(len(lines), index + after + 1)
        selected_indexes.update(range(start, end))

    footer_indexes = _find_failure_footer_indexes(lines)
    if footer_indexes and footer_indexes[-1] >= max(error_indexes):
        selected_indexes.update(footer_indexes)

    return _render_selected_lines(lines, sorted(selected_indexes))


def extract_error_context(
    log_text: str,
    context_lines: int = DEFAULT_CONTEXT_BEFORE,
    context_after: int = DEFAULT_CONTEXT_AFTER,
) -> str:
    """
    Keep the earlier parser helper name for existing callers.

    Args:
        log_text (str): Raw Jenkins console log.
        context_lines (int): Lines included before each error.
        context_after (int): Lines included after each error.

    Returns:
        str: Extracted error sections or final log lines.
    """
    return extract_relevant_log_lines(
        log_text,
        context_before=context_lines,
        context_after=context_after,
        tail_lines=context_lines,
    )


def _find_error_indexes(lines: list[str]) -> list[int]:
    """
    Find meaningful error lines, falling back to Jenkins wrapper errors.

    Args:
        lines (list[str]): Jenkins console log lines.

    Returns:
        list[int]: Zero-based indexes of selected error anchors.
    """
    meaningful_errors = [
        index
        for index, line in enumerate(lines)
        if ERROR_PATTERN.search(line)
    ]
    if meaningful_errors:
        return meaningful_errors

    return [
        index
        for index, line in enumerate(lines)
        if WRAPPER_ERROR_PATTERN.search(line)
    ]


def _find_failure_footer_indexes(lines: list[str]) -> list[int]:
    """
    Select the Jenkins wrapper footer section after a failure.

    Args:
        lines (list[str]): Jenkins console log lines.

    Returns:
        list[int]: Indexes from the nearest wrapper error through the footer.
    """
    footer_indexes = [
        index
        for index, line in enumerate(lines)
        if FAILURE_FOOTER_PATTERN.search(line)
    ]
    if not footer_indexes:
        return []

    footer_index = footer_indexes[-1]
    wrapper_index = next(
        (
            index
            for index in range(footer_index, -1, -1)
            if WRAPPER_ERROR_PATTERN.search(lines[index])
        ),
        None,
    )
    start_index = wrapper_index if wrapper_index is not None else footer_index
    return list(range(start_index, footer_index + 1))


def _render_selected_lines(lines: list[str], selected_indexes: list[int]) -> str:
    """
    Render selected lines with original line numbers and omission markers.

    Args:
        lines (list[str]): Full Jenkins console log lines.
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
