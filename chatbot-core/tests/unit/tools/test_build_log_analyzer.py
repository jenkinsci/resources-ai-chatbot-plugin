"""
Unit tests for Build Log Analyzer tool.

Tests the log fetching, error extraction, and analysis capabilities.
"""

import pytest
from unittest.mock import patch, MagicMock
from api.tools.build_log_analyzer import (
    extract_error_lines,
    identify_error_type,
    generate_search_queries,
    truncate_to_context_window,
    analyze_build_failure,
    analyze_build_failure_tool,
    fetch_jenkins_log,
)


class TestExtractErrorLines:
    """Tests for error line extraction."""

    def test_extracts_error_prefix_lines(self):
        """Lines starting with [ERROR] are extracted."""
        log = """
[INFO] Building project...
[ERROR] Failed to compile MyClass.java
[INFO] Build continuing...
"""
        lines = extract_error_lines(log)

        assert any("[ERROR]" in line for line in lines)
        assert any("Failed to compile" in line for line in lines)

    def test_extracts_fatal_lines(self):
        """Lines starting with [FATAL] are extracted."""
        log = """
[INFO] Starting build
[FATAL] Cannot allocate memory
[INFO] Exiting
"""
        lines = extract_error_lines(log)

        assert any("[FATAL]" in line for line in lines)

    def test_extracts_exception_lines(self):
        """Lines containing Exception are extracted."""
        log = """
Starting process
java.lang.NullPointerException
    at com.example.Main.run(Main.java:42)
Process complete
"""
        lines = extract_error_lines(log)

        assert any("NullPointerException" in line for line in lines)
        assert any("Main.java:42" in line for line in lines)

    def test_extracts_stack_trace_context(self):
        """Stack trace lines (starting with 'at') are captured."""
        log = """
Exception occurred:
    at com.example.ClassA.method(ClassA.java:10)
    at com.example.ClassB.call(ClassB.java:20)
    at com.example.Main.main(Main.java:5)
"""
        lines = extract_error_lines(log)

        assert any("ClassA.java:10" in line for line in lines)
        assert any("ClassB.java:20" in line for line in lines)

    def test_limits_extracted_lines(self):
        """Extraction respects max_lines limit."""
        # Generate many error lines
        error_lines_count = 200
        log = '\n'.join([f"[ERROR] Error line {i}" for i in range(error_lines_count)])

        lines = extract_error_lines(log, max_lines=50)

        # Should be limited, but may include context
        assert len(lines) <= 100  # Allow some buffer for context

    def test_prioritizes_later_errors(self):
        """Later errors in the log are prioritized."""
        log = """
[ERROR] Early error that was recovered
[INFO] Lots of info...
[INFO] More info...
[ERROR] The real failure cause at the end
"""
        lines = extract_error_lines(log, max_lines=10)

        # The later error should definitely be included
        assert any("real failure cause" in line for line in lines)

    def test_handles_empty_log(self):
        """Empty log returns empty list."""
        lines = extract_error_lines("")

        assert lines == []

    def test_handles_log_with_no_errors(self):
        """Log with no error patterns returns empty list."""
        log = """
[INFO] Build started
[INFO] Compiling sources
[INFO] Build successful
"""
        lines = extract_error_lines(log)

        assert lines == []


class TestIdentifyErrorType:
    """Tests for error type identification."""

    def test_identifies_null_pointer_exception(self):
        """NullPointerException is identified."""
        lines = ["java.lang.NullPointerException", "    at Main.main(Main.java:10)"]

        error_type = identify_error_type(lines)

        assert error_type == "NullPointerException"

    def test_identifies_out_of_memory(self):
        """OutOfMemoryError is identified."""
        lines = ["java.lang.OutOfMemoryError: Java heap space"]

        error_type = identify_error_type(lines)

        assert error_type == "OutOfMemoryError"

    def test_identifies_dependency_error(self):
        """Dependency resolution errors are identified."""
        lines = ["[ERROR] Could not resolve dependencies for project"]

        error_type = identify_error_type(lines)

        assert error_type == "DependencyResolutionError"

    def test_identifies_compilation_error(self):
        """Compilation errors are identified."""
        lines = ["[ERROR] COMPILATION FAILURE", "[ERROR] Missing semicolon"]

        error_type = identify_error_type(lines)

        assert error_type == "CompilationError"

    def test_identifies_test_failure(self):
        """Test failures are identified."""
        lines = ["[ERROR] Tests failed: 3 of 100"]

        error_type = identify_error_type(lines)

        assert error_type == "TestFailure"

    def test_identifies_npm_error(self):
        """npm errors are identified."""
        lines = ["npm ERR! code ENOENT", "npm ERR! syscall open"]

        error_type = identify_error_type(lines)

        assert error_type == "NpmError"

    def test_identifies_docker_error(self):
        """Docker errors are identified."""
        lines = ["Error response from Docker daemon: network not found"]

        error_type = identify_error_type(lines)

        assert error_type == "DockerError"

    def test_returns_none_for_unknown(self):
        """Unknown error types return None."""
        lines = ["Some random output", "That doesn't match patterns"]

        error_type = identify_error_type(lines)

        assert error_type is None


class TestGenerateSearchQueries:
    """Tests for search query generation."""

    def test_includes_error_type_in_query(self):
        """Error type is included in search queries."""
        queries = generate_search_queries(
            "NullPointerException",
            ["java.lang.NullPointerException"]
        )

        assert any("NullPointerException" in q for q in queries)
        assert any("Jenkins" in q for q in queries)

    def test_adds_maven_context(self):
        """Maven-related queries are added when maven is in logs."""
        queries = generate_search_queries(
            None,
            ["[INFO] Building with maven-compiler-plugin"]
        )

        assert any("Maven" in q for q in queries)

    def test_adds_npm_context(self):
        """npm-related queries are added when npm is in logs."""
        queries = generate_search_queries(
            None,
            ["npm run build failed"]
        )

        assert any("npm" in q for q in queries)

    def test_limits_query_count(self):
        """Query count is limited to 3."""
        queries = generate_search_queries(
            "TestFailure",
            ["Error 1", "Error 2", "Error 3", "Error 4", "Error 5"]
        )

        assert len(queries) <= 3


class TestTruncateToContextWindow:
    """Tests for context window truncation."""

    def test_preserves_short_text(self):
        """Short text is preserved unchanged."""
        text = "Short error message"

        result = truncate_to_context_window(text)

        assert result == text

    def test_truncates_long_text(self):
        """Long text is truncated with indicator."""
        text = "x" * 10000

        result = truncate_to_context_window(text, max_chars=1000)

        assert len(result) < len(text)
        assert "[truncated]" in result


class TestAnalyzeBuildFailure:
    """Tests for the main analysis function."""

    def test_handles_provided_log_content(self):
        """Can analyze pre-provided log content."""
        log = """
[INFO] Build started
[ERROR] NullPointerException in MyClass.java:42
    at com.example.MyClass.process(MyClass.java:42)
"""
        result = analyze_build_failure(
            "https://ci.jenkins.io/job/test/123/",
            log_content=log
        )

        assert result["success"] is True
        assert result["error_type"] == "NullPointerException"
        assert result["error_lines_count"] > 0

    def test_sanitizes_log_content(self):
        """Log content is sanitized before analysis."""
        log = """
[ERROR] Build failed
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
password=secret123
"""
        result = analyze_build_failure("http://jenkins/job/1/", log_content=log)

        # Secrets should not appear in sanitized context
        assert "AKIAIOSFODNN7EXAMPLE" not in result["sanitized_context"]
        assert "secret123" not in result["sanitized_context"]

    def test_generates_search_queries(self):
        """Search queries are generated for correlation."""
        log = """
[ERROR] Could not resolve dependencies for project
"""
        result = analyze_build_failure("http://jenkins/job/1/", log_content=log)

        assert "search_queries" in result
        assert len(result["search_queries"]) > 0

    def test_builds_analysis_prompt(self):
        """Analysis prompt is built for LLM."""
        log = "[ERROR] Test failure"

        result = analyze_build_failure("http://jenkins/job/1/", log_content=log)

        assert "analysis_prompt" in result
        assert "Error Log Excerpt" in result["analysis_prompt"]


class TestAnalyzeBuildFailureTool:
    """Tests for the tool wrapper function."""

    def test_returns_formatted_output(self):
        """Tool returns formatted string output."""
        log = "[ERROR] Build failed with NullPointerException"

        with patch('api.tools.build_log_analyzer.fetch_jenkins_log') as mock_fetch:
            mock_fetch.return_value = (log, None)

            result = analyze_build_failure_tool(
                "http://jenkins/job/1/",
                "analyze build failure",
                None
            )

        assert isinstance(result, str)
        assert "Build Failure Analysis" in result

    def test_handles_fetch_error(self):
        """Tool handles fetch errors gracefully."""
        with patch('api.tools.build_log_analyzer.fetch_jenkins_log') as mock_fetch:
            mock_fetch.return_value = (None, "Network error")

            result = analyze_build_failure_tool(
                "http://jenkins/job/1/",
                "analyze",
                None
            )

        assert "Failed to analyze" in result
        assert "Network error" in result


class TestFetchJenkinsLog:
    """Tests for Jenkins log fetching."""

    def test_handles_timeout(self):
        """Timeout errors are handled gracefully."""
        with patch('httpx.Client') as mock_client:
            import httpx
            mock_client.return_value.__enter__.return_value.get.side_effect = (
                httpx.TimeoutException("timeout")
            )

            log, error = fetch_jenkins_log("http://jenkins/job/1/")

        assert log is None
        assert "Timeout" in error

    def test_handles_404(self):
        """404 responses are handled gracefully."""
        with patch('httpx.Client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            log, error = fetch_jenkins_log("http://jenkins/job/nonexistent/")

        assert log is None
        assert "not found" in error

    def test_handles_401(self):
        """401 responses indicate auth requirement."""
        with patch('httpx.Client') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response

            log, error = fetch_jenkins_log("http://jenkins/job/1/")

        assert log is None
        assert "Authentication" in error


class TestMassiveLogs:
    """Tests for handling very large logs."""

    def test_handles_massive_log(self):
        """Very large logs are handled without memory issues."""
        # Simulate a 50,000 line log
        lines = [f"[INFO] Line {i}" for i in range(49000)]
        lines.extend([f"[ERROR] Error at line {49000 + i}" for i in range(1000)])
        log = '\n'.join(lines)

        result = analyze_build_failure("http://jenkins/job/1/", log_content=log)

        assert result["success"] is True
        # Context should be truncated
        assert len(result["sanitized_context"]) < len(log)
