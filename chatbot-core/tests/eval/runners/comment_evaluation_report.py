"""Publish the eval report as a single pull request comment."""

import argparse
import json
import os
from pathlib import Path
import time
from typing import Any
from urllib import error, parse, request

COMMENT_MARKER = "<!-- LLM-as-a-Judge-Evaluation-Report -->"
GITHUB_API_VERSION = "2022-11-28"
MAX_COMMENT_BYTES = 60_000
MAX_RETRIES = 3
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def call_github(url: str, method: str = "GET", body: dict | None = None) -> Any:
    """
    Call the GitHub REST API with retry and JSON handling.

    Args:
        url (str): GitHub API URL.
        method (str): HTTP method to use.
        body (dict | None): Optional JSON payload.

    Returns:
        Any: Parsed JSON response, or None for empty successful responses.
    """
    token = os.environ["GITHUB_TOKEN"]
    data = json.dumps(body).encode("utf-8") if body is not None else None
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        github_request = request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": GITHUB_API_VERSION,
            },
        )
        try:
            with request.urlopen(github_request, timeout=30) as response:  # nosec B310
                payload = response.read().decode("utf-8")
                if response.status == 204 or not payload.strip():
                    return None
                try:
                    return json.loads(payload)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"GitHub API returned invalid JSON for {method} {url}"
                    ) from exc
        except error.HTTPError as exc:
            last_error = exc
            if exc.code not in RETRYABLE_STATUS_CODES or attempt == MAX_RETRIES:
                details = exc.read().decode("utf-8", errors="replace").strip()
                raise RuntimeError(
                    f"GitHub API request failed for {method} {url}: "
                    f"HTTP {exc.code} {details}"
                ) from exc
        except error.URLError as exc:
            last_error = exc
            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"GitHub API request failed for {method} {url}: {exc.reason}"
                ) from exc

        time.sleep(min(2**attempt, 10))

    raise RuntimeError(
        f"GitHub API request failed for {method} {url}: {last_error}"
    )


def list_issue_comments(api_root: str, issue_number: str) -> list[dict[str, Any]]:
    """
    List all comments for the pull request issue number.

    Args:
        api_root (str): Repository GitHub API root URL.
        issue_number (str): Pull request issue number.

    Returns:
        list[dict[str, Any]]: All fetched issue comments.
    """
    comments: list[dict[str, Any]] = []
    page = 1
    per_page = 100
    while True:
        query = parse.urlencode({"per_page": per_page, "page": page})
        page_comments = call_github(
            f"{api_root}/issues/{issue_number}/comments?{query}"
        )
        if not isinstance(page_comments, list):
            raise RuntimeError("GitHub API returned an invalid comments payload")
        comments.extend(
            comment for comment in page_comments if isinstance(comment, dict)
        )
        if len(page_comments) < per_page:
            return comments
        page += 1


def is_actions_bot_comment(comment: dict[str, Any]) -> bool:
    """
    Return whether a comment was authored by the GitHub Actions bot.

    Args:
        comment (dict[str, Any]): GitHub issue comment payload.

    Returns:
        bool: True when the comment is a bot-authored eval comment candidate.
    """
    user = comment.get("user", {})
    if not isinstance(user, dict):
        return False
    login = user.get("login")
    user_type = user.get("type")
    return login == "github-actions[bot]" or user_type == "Bot"


def build_large_report_comment(
    report_text: str,
    commit_sha: str,
    workflow_run_url: str | None,
) -> str:
    """
    Build a shortened comment when the full report is too large.

    Args:
        report_text (str): Full Markdown evaluation report.
        commit_sha (str): Commit SHA evaluated by the workflow.
        workflow_run_url (str | None): URL of the evaluated workflow run.

    Returns:
        str: Shortened Markdown comment body.
    """
    excerpt = "\n".join(report_text.splitlines()[:20]).strip()
    lines = [
        COMMENT_MARKER,
        "# Chatbot evaluation report",
        "",
        "Full report omitted because it exceeds the GitHub comment size budget.",
        "",
        excerpt,
        "",
        f"Commit: `{commit_sha}`",
    ]
    if workflow_run_url:
        lines.append(f"Full report artifact: {workflow_run_url}")
    return "\n".join(lines)


def build_comment(
    report: Path,
    commit_sha: str,
    workflow_run_url: str | None,
) -> str:
    """
    Build the pull request comment body.

    Args:
        report (Path): Path to the generated Markdown evaluation report.
        commit_sha (str): Commit SHA evaluated by the workflow.
        workflow_run_url (str | None): URL of the evaluated workflow run.

    Returns:
        str: Markdown comment body.
    """
    report_text = report.read_text(encoding="utf-8")
    comment_body = "\n\n".join(
        [
            COMMENT_MARKER,
            report_text,
            f"Commit: `{commit_sha}`",
        ]
    )
    if len(comment_body.encode("utf-8")) <= MAX_COMMENT_BYTES:
        return comment_body
    return build_large_report_comment(report_text, commit_sha, workflow_run_url)


def main() -> int:
    """
    Create or update the existing eval report pull request comment.

    Returns:
        int: Zero when the comment is created, updated, or skipped.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--issue-number", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--workflow-run-id", default=None)
    args = parser.parse_args()

    if not args.report.exists():
        print(f"{args.report} does not exist; skipping PR comment.")
        return 0

    repository = os.environ["GITHUB_REPOSITORY"]
    server_url = os.getenv("GITHUB_SERVER_URL", "https://github.com")
    api_root = f"https://api.github.com/repos/{repository}"
    workflow_run_url = None
    if args.workflow_run_id:
        workflow_run_url = (
            f"{server_url}/{repository}/actions/runs/{args.workflow_run_id}"
        )
    comment_body = build_comment(args.report, args.commit_sha, workflow_run_url)
    comments = list_issue_comments(api_root, args.issue_number)
    existing_comments = [
        comment
        for comment in comments
        if COMMENT_MARKER in str(comment.get("body", ""))
        and is_actions_bot_comment(comment)
    ]
    existing_comment = existing_comments[-1] if existing_comments else None
    if existing_comment:
        comment_id = existing_comment.get("id")
        if not isinstance(comment_id, int):
            raise RuntimeError("Existing GitHub comment is missing a numeric id")
        call_github(
            f"{api_root}/issues/comments/{comment_id}",
            method="PATCH",
            body={"body": comment_body},
        )
        print(f"Updated comment {comment_id}.")
        return 0

    call_github(
        f"{api_root}/issues/{args.issue_number}/comments",
        method="POST",
        body={"body": comment_body},
    )
    print("Created evaluation report comment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
