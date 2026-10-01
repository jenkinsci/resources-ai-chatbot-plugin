"""Focused tests for Jenkins error-context extraction."""

from api.tools.log_parser import extract_error_context, extract_relevant_log_lines
from api.tools.sanitizer import sanitize_logs

def test_extracts_error_with_surrounding_context():
    """Include the configured lines around a meaningful error."""
    log = "\n".join(["checkout", "build", "deploy", "[ERROR] failed", "HTTP 401", "retrying"])

    assert extract_error_context(log, context_lines=2, context_after=2) == "\n".join(
        ["2: build", "3: deploy", "4: [ERROR] failed", "5: HTTP 401", "6: retrying"]
    )


def test_deduplicates_overlapping_context_and_marks_gaps():
    """Deduplicate nearby sections and mark omitted ranges between errors."""
    log = "\n".join(
        ["first", "shared", "[ERROR] early", "middle", "middle", "FATAL: late"]
    )
    result = extract_error_context(log, context_lines=0, context_after=0)

    assert result == "\n".join(
        [
            "3: [ERROR] early",
            "[... unrelated log lines omitted ...]",
            "6: FATAL: late",
        ]
    )

    nearby = extract_error_context("start\nshared\n[ERROR] one\n[FATAL] two", context_lines=2)
    assert nearby.count("shared") == 1
    assert nearby.count("[ERROR] one") == 1


def test_wrapper_error_is_fallback_anchor_but_can_be_context():
    """Use Jenkins wrapper errors as anchors only without meaningful errors."""
    meaningful = "\n".join(
        ["start", "[ERROR] failed", "details", "ERROR: script returned exit code 1"]
    )
    fallback = "\n".join(
        ["start", "build output", "ERROR: script returned exit code 1", "Finished: FAILURE"]
    )

    assert extract_error_context(meaningful, context_lines=0, context_after=3) == "\n".join(
        ["2: [ERROR] failed", "3: details", "4: ERROR: script returned exit code 1"]
    )
    assert extract_error_context(fallback, context_lines=1, context_after=1) == "\n".join(
        ["2: build output", "3: ERROR: script returned exit code 1", "4: Finished: FAILURE"]
    )


def test_keeps_failure_footer_after_meaningful_error():
    """Include Jenkins wrapper failure lines after a meaningful error section."""
    log = "\n".join(
        [
            "start",
            "[ERROR] deployment failed",
            "stack trace line",
            "[Pipeline] }",
            "[Pipeline] // stage",
            "ERROR: script returned exit code 1",
            "Finished: FAILURE",
        ]
    )

    assert extract_relevant_log_lines(
        log,
        context_before=0,
        context_after=0,
    ) == "\n".join(
        [
            "2: [ERROR] deployment failed",
            "[... unrelated log lines omitted ...]",
            "6: ERROR: script returned exit code 1",
            "7: Finished: FAILURE",
        ]
    )


def test_returns_configured_tail_when_no_error_matches():
    """Return the configured tail when the log has no recognized error."""
    log = "\n".join(["line 1", "line 2", "line 3"])

    assert extract_relevant_log_lines(log, context_before=2, tail_lines=2) == "line 2\nline 3"
    assert extract_relevant_log_lines(log, tail_lines=0) == ""


def test_sanitizes_selected_error_context():
    """Sanitize secrets after extracting a small error context."""
    log = "\n".join(
        [
            "start",
            "GITHUB_TOKEN=ghp_fakeFakeFakeFakeFakeFakeFakeFakeFakeFake",
            "[ERROR] failed",
            "HTTP 401",
            "end",
        ]
    )
    result = sanitize_logs(extract_error_context(log, context_lines=1, context_after=1))

    assert "GITHUB_TOKEN=[REDACTED]" in result
    assert "[ERROR] failed" in result
    assert "ghp_fake" not in result
