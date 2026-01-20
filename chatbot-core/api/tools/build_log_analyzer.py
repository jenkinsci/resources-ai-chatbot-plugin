"""
Build Log Analyzer Tool for Jenkins Build Failure Diagnosis.

This tool fetches build logs from Jenkins, sanitizes them, extracts relevant
error lines, and correlates with existing knowledge base for fix suggestions.
"""

import os
import re
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

import httpx

from api.services.sanitizer import sanitize_log_simple
from api.config.loader import CONFIG
from utils import LoggerFactory


logger = LoggerFactory.get_logger(__name__)

# Configuration with defaults
build_analysis_config = CONFIG.get("build_analysis", {})
MAX_LOG_LINES = build_analysis_config.get("max_log_lines", 100)
CONTEXT_WINDOW = build_analysis_config.get("context_window", 2000)
JENKINS_TIMEOUT = build_analysis_config.get("jenkins_timeout", 30)

# Patterns to identify error lines in build logs
ERROR_PATTERNS = [
    re.compile(r'^\[ERROR\]', re.MULTILINE),
    re.compile(r'^\[FATAL\]', re.MULTILINE),
    re.compile(r'^ERROR:', re.MULTILINE | re.IGNORECASE),
    re.compile(r'^FATAL:', re.MULTILINE | re.IGNORECASE),
    re.compile(r'Exception:', re.IGNORECASE),
    re.compile(r'Error:', re.IGNORECASE),
    re.compile(r'BUILD FAILED', re.IGNORECASE),
    re.compile(r'FAILURE', re.IGNORECASE),
    re.compile(r'Failed to', re.IGNORECASE),
    re.compile(r'Could not', re.IGNORECASE),
    re.compile(r'Cannot ', re.IGNORECASE),
    re.compile(r'^\s+at\s+[\w.$]+\(', re.MULTILINE),  # Stack trace lines
]


@dataclass
class BuildLogAnalysis:
    """Result of build log analysis."""
    build_url: str
    error_summary: str
    error_lines: List[str]
    sanitized_context: str
    suggested_searches: List[str]
    error_type: Optional[str] = None


def fetch_jenkins_log(build_url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Fetch the console log from a Jenkins build.

    Args:
        build_url: The Jenkins build URL (e.g., https://ci.jenkins.io/job/Core/.../123/)

    Returns:
        Tuple of (log_content, error_message). If successful, error_message is None.
    """
    # Normalize URL and construct console text URL
    build_url = build_url.rstrip('/')
    console_url = f"{build_url}/consoleText"

    # Get Jenkins credentials from environment
    jenkins_user = os.environ.get("JENKINS_USER")
    jenkins_token = os.environ.get("JENKINS_API_TOKEN")

    try:
        # Build request with optional authentication
        headers = {"Accept": "text/plain"}
        auth = None
        if jenkins_user and jenkins_token:
            auth = (jenkins_user, jenkins_token)

        with httpx.Client(timeout=JENKINS_TIMEOUT) as client:
            response = client.get(console_url, headers=headers, auth=auth)

            if response.status_code == 200:
                return response.text, None
            if response.status_code == 401:
                return None, "Authentication required. Set JENKINS_USER and JENKINS_API_TOKEN."
            if response.status_code == 404:
                return None, f"Build not found: {build_url}"
            return None, f"Jenkins API error: {response.status_code}"

    except httpx.TimeoutException:
        return None, f"Timeout fetching log from {console_url}"
    except httpx.RequestError as exc:
        return None, f"Network error: {str(exc)}"


def extract_error_lines(log_content: str, max_lines: int = MAX_LOG_LINES) -> List[str]:
    """
    Extract lines that appear to be errors from a build log.

    Uses a sliding window approach to capture context around error lines.

    Args:
        log_content: The full build log content.
        max_lines: Maximum number of error lines to extract.

    Returns:
        List of error lines with some surrounding context.
    """
    lines = log_content.split('\n')
    error_indices = set()

    # Find all lines matching error patterns
    for i, line in enumerate(lines):
        for pattern in ERROR_PATTERNS:
            if pattern.search(line):
                # Include this line and some context (2 lines before, 5 after for stack traces)
                for j in range(max(0, i - 2), min(len(lines), i + 6)):
                    error_indices.add(j)
                break

    # Convert to sorted list and extract lines
    sorted_indices = sorted(error_indices)

    # Prioritize later errors (usually more relevant)
    if len(sorted_indices) > max_lines:
        # Take the last N indices
        sorted_indices = sorted_indices[-max_lines:]

    return [lines[i] for i in sorted_indices if i < len(lines)]


def identify_error_type(error_lines: List[str]) -> Optional[str]:
    """
    Identify the type of error from the extracted error lines.

    Args:
        error_lines: List of extracted error lines.

    Returns:
        String identifying the error type, or None if unknown.
    """
    combined = '\n'.join(error_lines)

    # Common Java/Maven errors
    if 'NullPointerException' in combined:
        return "NullPointerException"
    if 'OutOfMemoryError' in combined:
        return "OutOfMemoryError"
    if 'ClassNotFoundException' in combined:
        return "ClassNotFoundException"
    if 'NoSuchMethodError' in combined:
        return "NoSuchMethodError"
    if 'Could not resolve dependencies' in combined:
        return "DependencyResolutionError"
    if 'compilation failure' in combined.lower():
        return "CompilationError"
    if 'test failure' in combined.lower() or 'tests failed' in combined.lower():
        return "TestFailure"

    # Common build tool errors
    if 'npm ERR!' in combined:
        return "NpmError"
    if 'pip install' in combined.lower() and 'error' in combined.lower():
        return "PipInstallError"

    # Common CI/CD errors
    if 'docker' in combined.lower() and 'error' in combined.lower():
        return "DockerError"
    if 'permission denied' in combined.lower():
        return "PermissionError"
    if 'connection refused' in combined.lower() or 'timeout' in combined.lower():
        return "NetworkError"

    return None


def generate_search_queries(error_type: Optional[str], error_lines: List[str]) -> List[str]:
    """
    Generate search queries that can be used to find similar issues.

    Args:
        error_type: The identified error type.
        error_lines: The extracted error lines.

    Returns:
        List of search query strings.
    """
    queries = []

    if error_type:
        queries.append(f"Jenkins {error_type} fix solution")

    # Extract the most relevant error message
    for line in error_lines:
        # Look for exception messages
        if 'Exception' in line or 'Error' in line:
            # Clean up the line for searching
            cleaned = re.sub(r'\[[\w\-:]+\]\s*', '', line)  # Remove timestamps
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            if 15 < len(cleaned) < 200:  # Reasonable query length
                queries.append(cleaned)
                break

    # Add a generic query based on content
    if 'maven' in '\n'.join(error_lines).lower():
        queries.append("Jenkins Maven build failure troubleshooting")
    elif 'gradle' in '\n'.join(error_lines).lower():
        queries.append("Jenkins Gradle build failure troubleshooting")
    elif 'npm' in '\n'.join(error_lines).lower():
        queries.append("Jenkins npm build failure troubleshooting")

    return queries[:3]  # Limit to 3 queries


def truncate_to_context_window(text: str, max_chars: int = CONTEXT_WINDOW * 4) -> str:
    """
    Truncate text to fit within context window.

    Args:
        text: The text to truncate.
        max_chars: Maximum characters (approximate tokens * 4).

    Returns:
        Truncated text.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


def analyze_build_failure(
    build_url: str,
    log_content: Optional[str] = None
) -> Dict:
    """
    Analyze a Jenkins build failure.

    This is the main tool function that can be called by the agent.

    Args:
        build_url: The Jenkins build URL to analyze.
        log_content: Optional pre-fetched log content (for testing).

    Returns:
        Dict containing analysis results suitable for LLM context.
    """
    logger.info("Analyzing build failure: %s", build_url)

    # Fetch log if not provided
    if log_content is None:
        log_content, error = fetch_jenkins_log(build_url)
        if error:
            logger.error("Failed to fetch log: %s", error)
            return {
                "success": False,
                "error": error,
                "build_url": build_url
            }

    # Sanitize the log content (CRITICAL for security)
    sanitized_log = sanitize_log_simple(log_content)
    logger.info("Log sanitized, original: %d chars, sanitized: %d chars",
                len(log_content), len(sanitized_log))

    # Extract error lines
    error_lines = extract_error_lines(sanitized_log)
    logger.info("Extracted %d error lines", len(error_lines))

    # Identify error type
    error_type = identify_error_type(error_lines)
    if error_type:
        logger.info("Identified error type: %s", error_type)

    # Generate search queries for vector database correlation
    search_queries = generate_search_queries(error_type, error_lines)

    # Build context for LLM
    error_context = '\n'.join(error_lines)
    sanitized_context = truncate_to_context_window(error_context)

    # Create summary
    error_summary = f"Build failure analysis for {build_url}"
    if error_type:
        error_summary += f" - Detected: {error_type}"

    return {
        "success": True,
        "build_url": build_url,
        "error_type": error_type,
        "error_summary": error_summary,
        "error_lines_count": len(error_lines),
        "sanitized_context": sanitized_context,
        "search_queries": search_queries,
        "analysis_prompt": _build_analysis_prompt(
            error_type, error_lines, search_queries
        )
    }


def _build_analysis_prompt(
    error_type: Optional[str],
    error_lines: List[str],
    search_queries: List[str]
) -> str:
    """
    Build a prompt for the LLM to analyze the build failure.

    Args:
        error_type: Identified error type.
        error_lines: Extracted error lines.
        search_queries: Generated search queries.

    Returns:
        Formatted prompt string.
    """
    prompt_parts = [
        "Analyze this Jenkins build failure and provide:",
        "1. A clear explanation of what went wrong",
        "2. The root cause if identifiable",
        "3. Specific steps to fix the issue",
        "",
    ]

    if error_type:
        prompt_parts.append(f"**Detected Error Type**: {error_type}")
        prompt_parts.append("")

    prompt_parts.append("**Error Log Excerpt**:")
    prompt_parts.append("```")
    prompt_parts.extend(error_lines[:50])  # Limit for prompt size
    prompt_parts.append("```")

    if search_queries:
        prompt_parts.append("")
        prompt_parts.append("**Related Search Topics**:")
        for query in search_queries:
            prompt_parts.append(f"- {query}")

    return '\n'.join(prompt_parts)


# Expose for TOOL_REGISTRY with proper signature
def analyze_build_failure_tool(
    build_url: str,
    query: str,  # pylint: disable=unused-argument
    logger_instance=None  # pylint: disable=unused-argument
) -> str:
    """
    Tool wrapper for analyze_build_failure that matches expected signature.

    Args:
        build_url: The Jenkins build URL to analyze.
        query: The original user query (for context).
        logger_instance: Logger (unused, uses module logger).

    Returns:
        String result suitable for chat context.
    """
    result = analyze_build_failure(build_url)

    if not result.get("success"):
        return f"Failed to analyze build: {result.get('error', 'Unknown error')}"

    output_parts = [
        f"## Build Failure Analysis",
        f"**Build URL**: {result['build_url']}",
    ]

    if result.get("error_type"):
        output_parts.append(f"**Error Type**: {result['error_type']}")

    output_parts.append(f"\n**Error Context** ({result['error_lines_count']} lines):")
    output_parts.append("```")
    output_parts.append(result.get("sanitized_context", "No context available"))
    output_parts.append("```")

    if result.get("search_queries"):
        output_parts.append("\n**Suggested Searches**:")
        for query_str in result["search_queries"]:
            output_parts.append(f"- {query_str}")

    return '\n'.join(output_parts)
