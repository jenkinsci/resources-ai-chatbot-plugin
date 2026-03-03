"""Unit tests for private helper functions in chat_service.py (issue #219).

Tests cover:
- _process_file_context
- _format_user_message_for_memory
- _extract_query_type
- _extract_relevance_score
- _assemble_response
- _generate_search_query_from_logs
- LOG_ANALYSIS_PATTERN regex
"""

import re
import pytest
from unittest.mock import MagicMock, patch

from api.models.schemas import FileAttachment, FileType


# ---------------------------------------------------------------------------
# _process_file_context
# ---------------------------------------------------------------------------
class TestProcessFileContext:
    """Tests for _process_file_context helper."""

    def test_returns_context_unchanged_when_no_files(self):
        from api.services.chat_service import _process_file_context
        result = _process_file_context("existing context", None)
        assert result == "existing context"

    def test_returns_context_unchanged_when_empty_files(self):
        from api.services.chat_service import _process_file_context
        result = _process_file_context("existing context", [])
        assert result == "existing context"

    @patch("api.services.chat_service.format_file_context")
    def test_appends_file_context_when_files_provided(self, mock_fmt):
        from api.services.chat_service import _process_file_context
        mock_fmt.return_value = "file content here"
        files = [
            FileAttachment(
                filename="test.py",
                type=FileType.TEXT,
                content="print('hello')",
                mime_type="text/plain",
            )
        ]
        result = _process_file_context("base context", files)
        assert "base context" in result
        assert "[User Uploaded Files]" in result
        assert "file content here" in result
        mock_fmt.assert_called_once()

    @patch("api.services.chat_service.format_file_context")
    def test_returns_original_when_file_context_empty(self, mock_fmt):
        from api.services.chat_service import _process_file_context
        mock_fmt.return_value = ""
        files = [
            FileAttachment(
                filename="empty.txt",
                type=FileType.TEXT,
                content="",
                mime_type="text/plain",
            )
        ]
        result = _process_file_context("base context", files)
        assert result == "base context"

    @patch("api.services.chat_service.format_file_context")
    def test_handles_multiple_files(self, mock_fmt):
        from api.services.chat_service import _process_file_context
        mock_fmt.return_value = "combined file output"
        files = [
            FileAttachment(
                filename="a.py", type=FileType.TEXT,
                content="aaa", mime_type="text/plain",
            ),
            FileAttachment(
                filename="b.py", type=FileType.TEXT,
                content="bbb", mime_type="text/plain",
            ),
        ]
        result = _process_file_context("ctx", files)
        assert "combined file output" in result
        # format_file_context receives list of dicts
        call_args = mock_fmt.call_args[0][0]
        assert len(call_args) == 2


# ---------------------------------------------------------------------------
# _format_user_message_for_memory
# ---------------------------------------------------------------------------
class TestFormatUserMessageForMemory:
    """Tests for _format_user_message_for_memory helper."""

    def test_returns_input_when_no_files(self):
        from api.services.chat_service import _format_user_message_for_memory
        assert _format_user_message_for_memory("hello", None) == "hello"

    def test_returns_input_when_empty_files(self):
        from api.services.chat_service import _format_user_message_for_memory
        assert _format_user_message_for_memory("hello", []) == "hello"

    def test_appends_single_filename(self):
        from api.services.chat_service import _format_user_message_for_memory
        files = [
            FileAttachment(
                filename="report.pdf", type=FileType.TEXT,
                content="...", mime_type="application/pdf",
            )
        ]
        result = _format_user_message_for_memory("check this", files)
        assert "check this" in result
        assert "report.pdf" in result
        assert "[Attached files:" in result

    def test_appends_multiple_filenames(self):
        from api.services.chat_service import _format_user_message_for_memory
        files = [
            FileAttachment(
                filename="a.py", type=FileType.TEXT,
                content="", mime_type="text/plain",
            ),
            FileAttachment(
                filename="b.png", type=FileType.IMAGE,
                content="", mime_type="image/png",
            ),
        ]
        result = _format_user_message_for_memory("review", files)
        assert "a.py" in result
        assert "b.png" in result


# ---------------------------------------------------------------------------
# _extract_query_type
# ---------------------------------------------------------------------------
class TestExtractQueryType:
    """Tests for _extract_query_type regex extraction."""

    def test_extracts_simple(self):
        from api.services.chat_service import _extract_query_type
        assert _extract_query_type("The query type is SIMPLE.") == "SIMPLE"

    def test_extracts_multi(self):
        from api.services.chat_service import _extract_query_type
        assert _extract_query_type("This is a MULTI query.") == "MULTI"

    def test_case_insensitive(self):
        from api.services.chat_service import _extract_query_type
        assert _extract_query_type("simple") == "SIMPLE"
        assert _extract_query_type("multi") == "MULTI"
        assert _extract_query_type("Simple") == "SIMPLE"

    def test_returns_empty_for_no_match(self):
        from api.services.chat_service import _extract_query_type
        assert _extract_query_type("something else entirely") == ""

    def test_returns_empty_for_empty_string(self):
        from api.services.chat_service import _extract_query_type
        assert _extract_query_type("") == ""

    def test_first_match_wins(self):
        from api.services.chat_service import _extract_query_type
        # re.search returns the first match
        result = _extract_query_type("SIMPLE then MULTI")
        assert result == "SIMPLE"

    def test_word_boundary_respected(self):
        from api.services.chat_service import _extract_query_type
        # "SIMPLEST" should still match "SIMPLE" due to \b at start
        # but the \b at end should prevent matching inside a word
        assert _extract_query_type("MULTITASK") == ""


# ---------------------------------------------------------------------------
# _extract_relevance_score
# ---------------------------------------------------------------------------
class TestExtractRelevanceScore:
    """Tests for _extract_relevance_score regex extraction."""

    def test_extracts_relevant(self):
        from api.services.chat_service import _extract_relevance_score
        assert _extract_relevance_score("Label: 1") == 1

    def test_extracts_not_relevant(self):
        from api.services.chat_service import _extract_relevance_score
        assert _extract_relevance_score("Label: 0") == 0

    def test_case_insensitive(self):
        from api.services.chat_service import _extract_relevance_score
        assert _extract_relevance_score("label: 1") == 1
        assert _extract_relevance_score("LABEL: 0") == 0

    def test_defaults_to_zero_when_no_match(self):
        from api.services.chat_service import _extract_relevance_score
        assert _extract_relevance_score("no label here") == 0

    def test_defaults_to_zero_for_empty_string(self):
        from api.services.chat_service import _extract_relevance_score
        assert _extract_relevance_score("") == 0

    def test_extracts_from_multiline(self):
        from api.services.chat_service import _extract_relevance_score
        response = "The context is relevant.\n\nLabel: 1"
        assert _extract_relevance_score(response) == 1

    def test_ignores_labels_with_other_numbers(self):
        from api.services.chat_service import _extract_relevance_score
        # Only 0 or 1 should match
        assert _extract_relevance_score("Label: 5") == 0

    def test_handles_extra_whitespace(self):
        from api.services.chat_service import _extract_relevance_score
        assert _extract_relevance_score("Label:  1") == 1
        assert _extract_relevance_score("Label:   0") == 0


# ---------------------------------------------------------------------------
# _assemble_response
# ---------------------------------------------------------------------------
class TestAssembleResponse:
    """Tests for _assemble_response helper."""

    def test_joins_multiple_answers(self):
        from api.services.chat_service import _assemble_response
        result = _assemble_response(["answer 1", "answer 2", "answer 3"])
        assert result == "answer 1\n\nanswer 2\n\nanswer 3"

    def test_single_answer(self):
        from api.services.chat_service import _assemble_response
        result = _assemble_response(["only one"])
        assert result == "only one"

    def test_empty_list(self):
        from api.services.chat_service import _assemble_response
        result = _assemble_response([])
        assert result == ""

    def test_preserves_whitespace_in_answers(self):
        from api.services.chat_service import _assemble_response
        result = _assemble_response(["  spaced  ", "\ttabbed\t"])
        assert "  spaced  " in result
        assert "\ttabbed\t" in result


# ---------------------------------------------------------------------------
# LOG_ANALYSIS_PATTERN
# ---------------------------------------------------------------------------
class TestLogAnalysisPattern:
    """Tests for LOG_ANALYSIS_PATTERN regex."""

    def test_matches_standard_log_block(self):
        from api.services.chat_service import LOG_ANALYSIS_PATTERN
        text = (
            "Here are the last 500 characters of the log:\n"
            "```\n"
            "ERROR: Build failed\njava.lang.NullPointerException\n"
            "```\n"
            "What went wrong?"
        )
        match = LOG_ANALYSIS_PATTERN.search(text)
        assert match is not None
        assert "NullPointerException" in match.group(1)
        assert "What went wrong?" in match.group(2)

    def test_matches_different_character_counts(self):
        from api.services.chat_service import LOG_ANALYSIS_PATTERN
        for count in ["100", "5000", "99999"]:
            text = f"Here are the last {count} characters of the log:\n```\nsome log\n```\nquestion"
            assert LOG_ANALYSIS_PATTERN.search(text) is not None

    def test_no_match_without_log_prefix(self):
        from api.services.chat_service import LOG_ANALYSIS_PATTERN
        text = "```\nsome code\n```\nWhat is this?"
        assert LOG_ANALYSIS_PATTERN.search(text) is None

    def test_no_match_plain_text(self):
        from api.services.chat_service import LOG_ANALYSIS_PATTERN
        assert LOG_ANALYSIS_PATTERN.search("How do I install Jenkins?") is None

    def test_captures_multiline_log(self):
        from api.services.chat_service import LOG_ANALYSIS_PATTERN
        text = (
            "Here are the last 1000 characters of the log:\n"
            "```\n"
            "line 1\nline 2\nline 3\n"
            "```\n"
            "Please help"
        )
        match = LOG_ANALYSIS_PATTERN.search(text)
        assert match is not None
        assert "line 1" in match.group(1)
        assert "line 3" in match.group(1)


# ---------------------------------------------------------------------------
# _generate_search_query_from_logs
# ---------------------------------------------------------------------------
@patch("api.services.chat_service.generate_answer")
class TestGenerateSearchQueryFromLogs:
    """Tests for _generate_search_query_from_logs helper."""

    def test_returns_stripped_llm_output(self, mock_generate):
        from api.services.chat_service import _generate_search_query_from_logs
        mock_generate.return_value = "  Jenkins pipeline exit code 1  "
        result = _generate_search_query_from_logs("ERROR: exit code 1")
        assert result == "Jenkins pipeline exit code 1"

    def test_passes_log_text_to_prompt(self, mock_generate):
        from api.services.chat_service import _generate_search_query_from_logs
        mock_generate.return_value = "query"
        _generate_search_query_from_logs("my log content")
        call_args = mock_generate.call_args[0][0]
        assert "my log content" in call_args

    def test_handles_empty_llm_output(self, mock_generate):
        from api.services.chat_service import _generate_search_query_from_logs
        mock_generate.return_value = "   "
        result = _generate_search_query_from_logs("some log")
        assert result == ""

    def test_handles_multiline_llm_output(self, mock_generate):
        from api.services.chat_service import _generate_search_query_from_logs
        mock_generate.return_value = "first line\nsecond line"
        result = _generate_search_query_from_logs("log")
        assert result == "first line\nsecond line"
