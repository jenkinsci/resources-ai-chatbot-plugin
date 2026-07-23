"""Extract relevant failure sections from Jenkins build logs."""

import re


DEFAULT_CONTEXT_BEFORE = 20
DEFAULT_CONTEXT_AFTER = 10
DEFAULT_TAIL_LINES = 100
DEFAULT_MAX_CHARS = 12000
DEFAULT_MAX_ERROR_MATCHES = 10

ERROR_PATTERNS = (
    re.compile(r"\b(?:ERROR|FATAL)\b"),
    re.compile(r"\b[\w.$]*(?:Exception|Error)\b"),
    re.compile(r"\bBUILD FAILURE\b", re.IGNORECASE),
    re.compile(r"\bFAILURE: Build failed\b", re.IGNORECASE),
    re.compile(r"\bExecution failed for task\b", re.IGNORECASE),
    re.compile(r"\b(?:exit code|exited with code)\s+\d+\b", re.IGNORECASE),
    re.compile(r"\breturned non-zero exit status\b", re.IGNORECASE),
    re.compile(r"\bCaused by:", re.IGNORECASE),
    re.compile(r"\bcompilation (?:error|failure)\b", re.IGNORECASE),
    re.compile(r":\d+:\s+error:", re.IGNORECASE),
    re.compile(r"\bTraceback \(most recent call last\):"),
)


def extract_relevant_log_lines(
    log_text: str,
    context_before: int = DEFAULT_CONTEXT_BEFORE,
    context_after: int = DEFAULT_CONTEXT_AFTER,
    tail_lines: int = DEFAULT_TAIL_LINES,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> str:
    """
    Extract error lines, nearby context, and recent tail output.

    Args:
        log_text (str): Full sanitized Jenkins console log.
        context_before (int): Number of lines to keep before each match.
        context_after (int): Number of lines to keep after each match.
        tail_lines (int): Number of final log lines to include.
        max_chars (int): Maximum output characters.

    Returns:
        str: Relevant log snippet capped to the character budget.
    """
    if not log_text or max_chars <= 0:
        return ""

    lines = log_text.splitlines()
    if not lines:
        return ""

    error_line_numbers = find_error_line_numbers(lines)
    recent_error_line_numbers = error_line_numbers[-DEFAULT_MAX_ERROR_MATCHES:]
    selected_line_numbers = select_line_numbers(
        line_count=len(lines),
        error_line_numbers=recent_error_line_numbers,
        context_before=context_before,
        context_after=context_after,
        tail_lines=tail_lines,
    )

    return trim_to_character_budget(
        render_selected_lines(lines, selected_line_numbers),
        max_chars,
    )


def find_error_line_numbers(lines: list[str]) -> list[int]:
    """
    Find line numbers that match common build failure patterns.

    Args:
        lines (list[str]): Console log lines.

    Returns:
        list[int]: Zero-based indexes of matching lines.
    """
    return [
        index
        for index, line in enumerate(lines)
        if any(pattern.search(line) for pattern in ERROR_PATTERNS)
    ]


def select_line_numbers(
    line_count: int,
    error_line_numbers: list[int],
    context_before: int,
    context_after: int,
    tail_lines: int,
) -> list[int]:
    """
    Select context and tail line numbers while preserving log order.

    Args:
        line_count (int): Total number of lines in the log.
        error_line_numbers (list[int]): Lines that matched failure patterns.
        context_before (int): Number of lines to keep before each match.
        context_after (int): Number of lines to keep after each match.
        tail_lines (int): Number of final log lines to keep.

    Returns:
        list[int]: Deduplicated line numbers in ascending order.
    """
    selected: set[int] = set()
    before = max(0, context_before)
    after = max(0, context_after)

    for line_number in error_line_numbers:
        start = max(0, line_number - before)
        end = min(line_count, line_number + after + 1)
        selected.update(range(start, end))

    tail_start = max(0, line_count - max(0, tail_lines))
    selected.update(range(tail_start, line_count))

    return sorted(selected)


def render_selected_lines(
    lines: list[str],
    selected_line_numbers: list[int],
) -> str:
    """
    Render selected lines with line numbers and omission markers.

    Args:
        lines (list[str]): Full log lines.
        selected_line_numbers (list[int]): Selected zero-based line numbers.

    Returns:
        str: Rendered log text.
    """
    output_lines: list[str] = []
    previous_line: int | None = None

    for line_number in selected_line_numbers:
        if previous_line is not None and line_number > previous_line + 1:
            omitted = line_number - previous_line - 1
            output_lines.append(f"[... {omitted} log lines omitted ...]")

        output_lines.append(f"{line_number + 1}: {lines[line_number]}")
        previous_line = line_number

    return "\n".join(output_lines)


def trim_to_character_budget(text: str, max_chars: int) -> str:
    """
    Keep the most recent selected output within the character budget.

    Args:
        text (str): Rendered selected log text.
        max_chars (int): Maximum output characters.

    Returns:
        str: Text capped to the character budget.
    """
    if len(text) <= max_chars:
        return text

    marker = "[... earlier selected log output omitted ...]\n"
    available_chars = max_chars - len(marker)
    if available_chars <= 0:
        return marker[:max_chars]

    kept_lines: list[str] = []
    used_chars = 0
    for line in reversed(text.splitlines()):
        line_chars = len(line) + (1 if kept_lines else 0)
        if used_chars + line_chars > available_chars:
            break
        kept_lines.append(line)
        used_chars += line_chars

    if not kept_lines:
        return marker + text[-available_chars:]

    return marker + "\n".join(reversed(kept_lines))
