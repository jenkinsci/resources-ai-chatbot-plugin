"""Publish the eval report as a single pull request comment."""

import argparse
import json
import os
from pathlib import Path
from typing import Any
from urllib import request

COMMENT_MARKER = "<!-- LLM-as-a-Judge-Evaluation-Report -->"


def call_github(url: str, method: str = "GET", body: dict | None = None) -> Any:
    """
    Call the GitHub REST API with the workflow token.

    Args:
        url (str): GitHub API URL.
        method (str): HTTP method to use.
        body (dict | None): Optional JSON payload.

    Returns:
        Any: Parsed JSON response.
    """
    token = os.environ["GITHUB_TOKEN"]
    data = json.dumps(body).encode("utf-8") if body is not None else None
    github_request = request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with request.urlopen(github_request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def build_comment(report: Path, commit_sha: str) -> str:
    """
    Build the pull request comment body.

    Args:
        report (Path): Path to the generated Markdown evaluation report.
        commit_sha (str): Commit SHA evaluated by the workflow.

    Returns:
        str: Markdown comment body.
    """
    return "\n\n".join(
        [
            COMMENT_MARKER,
            report.read_text(encoding="utf-8"),
            f"Commit: `{commit_sha}`",
        ]
    )


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
    args = parser.parse_args()

    if not args.report.exists():
        print(f"{args.report} does not exist; skipping PR comment.")
        return 0

    repository = os.environ["GITHUB_REPOSITORY"]
    api_root = f"https://api.github.com/repos/{repository}"
    comment_body = build_comment(args.report, args.commit_sha)
    comments = call_github(
        f"{api_root}/issues/{args.issue_number}/comments?per_page=100"
    )
    existing_comment = next(
        (
            comment
            for comment in comments
            if COMMENT_MARKER in comment.get("body", "")
            and comment.get("user", {}).get("type") == "Bot"
        ),
        None,
    )
    if existing_comment:
        call_github(
            f"{api_root}/issues/comments/{existing_comment['id']}",
            method="PATCH",
            body={"body": comment_body},
        )
        print(f"Updated comment {existing_comment['id']}.")
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
