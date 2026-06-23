"""Resolve the latest successful retrieval vector cache artifact."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any
from urllib import parse, request
from urllib.error import HTTPError, URLError

GITHUB_API_URL = "https://api.github.com"


def default_artifact_name() -> str:
    """
    Build the default cache artifact name for the current UTC day.

    Returns:
        str: Cache artifact name using a DDMM suffix.
    """
    return f"retrieval-vector-database-{datetime.now(timezone.utc):%d%m}"


def github_api_get(path: str, token: str) -> dict[str, Any]:
    """
    Fetch a JSON object from the GitHub REST API.

    Args:
        path (str): API path beginning with a slash.
        token (str): GitHub token with Actions read access.

    Returns:
        dict[str, Any]: Parsed JSON response.

    Raises:
        RuntimeError: If the API request fails or returns a non-object payload.
    """
    api_request = request.Request(
        GITHUB_API_URL + path,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with request.urlopen(api_request, timeout=30) as response:  # nosec B310
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"GitHub API request failed for {path}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError(f"GitHub API returned a non-object payload for {path}")
    return payload


def list_recent_workflow_runs(
    repository: str,
    branch: str | None,
    token: str,
) -> list[dict[str, Any]]:
    """
    List recent workflow runs that could contain the retrieval cache artifact.

    Args:
        repository (str): Repository in OWNER/REPO format.
        branch (str | None): Optional branch used to narrow the run search.
        token (str): GitHub token with Actions read access.

    Returns:
        list[dict[str, Any]]: Recent workflow run records.
    """
    query_params: dict[str, str | int] = {"per_page": 20}
    if branch:
        query_params["branch"] = branch
    query = parse.urlencode(query_params)
    payload = github_api_get(
        f"/repos/{repository}/actions/runs?{query}",
        token,
    )
    runs = payload.get("workflow_runs", [])
    if not isinstance(runs, list):
        raise RuntimeError("GitHub API workflow_runs payload is invalid")
    return [run for run in runs if isinstance(run, dict)]


def run_has_artifact(
    repository: str,
    run_id: int,
    artifact_name: str,
    token: str,
) -> bool:
    """
    Check whether a workflow run has the required non-expired artifact.

    Args:
        repository (str): Repository in OWNER/REPO format.
        run_id (int): Workflow run identifier.
        artifact_name (str): Artifact name to find.
        token (str): GitHub token with Actions read access.

    Returns:
        bool: True when the run has a matching artifact that is not expired.
    """
    payload = github_api_get(
        f"/repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100",
        token,
    )
    artifacts = payload.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise RuntimeError("GitHub API artifacts payload is invalid")

    return any(
        isinstance(artifact, dict)
        and artifact.get("name") == artifact_name
        and artifact.get("expired") is False
        for artifact in artifacts
    )


def resolve_run_id(
    repository: str,
    branch: str | None,
    artifact_name: str,
    token: str,
) -> int:
    """
    Resolve the latest successful workflow run containing the cache artifact.

    Args:
        repository (str): Repository in OWNER/REPO format.
        branch (str | None): Optional branch used to narrow the run search.
        artifact_name (str): Required artifact name.
        token (str): GitHub token with Actions read access.

    Returns:
        int: Workflow run ID that contains the requested artifact.

    Raises:
        RuntimeError: If no valid cache artifact can be found.
    """
    for run in list_recent_workflow_runs(repository, branch, token):
        run_id = run.get("id")
        if isinstance(run_id, int) and run_has_artifact(
            repository,
            run_id,
            artifact_name,
            token,
        ):
            return run_id

    raise RuntimeError(
        f"No non-expired '{artifact_name}' artifact found in recent workflow "
        "runs. The fallback cache build will run."
    )


def write_github_output(
    output_path: Path,
    artifact_name: str,
    cache_found: bool,
    run_id: int | None = None,
) -> None:
    """
    Append cache lookup results to a GitHub Actions output file.

    Args:
        output_path (Path): Path from the GITHUB_OUTPUT environment variable.
        artifact_name (str): Cache artifact name used for lookup.
        cache_found (bool): Whether a reusable cache artifact was found.
        run_id (int | None): Workflow run ID that owns the artifact, if found.
    """
    with output_path.open("a", encoding="utf-8") as output_file:
        output_file.write(f"artifact_name={artifact_name}\n")
        output_file.write(f"cache_found={str(cache_found).lower()}\n")
        output_file.write(f"run_id={run_id or ''}\n")


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for artifact resolution.

    Returns:
        argparse.Namespace: Parsed CLI arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--branch")
    parser.add_argument("--artifact-name", default=default_artifact_name())
    parser.add_argument("--github-output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    """
    Resolve and export the retrieval cache workflow run ID.

    Returns:
        int: Zero after exporting whether a cache was found.
    """
    args = parse_args()
    try:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN is required to read workflow artifacts")
        if not args.repository:
            raise RuntimeError("--repository or GITHUB_REPOSITORY is required")

        run_id = resolve_run_id(
            repository=args.repository,
            branch=args.branch,
            artifact_name=args.artifact_name,
            token=token,
        )
        write_github_output(
            args.github_output,
            artifact_name=args.artifact_name,
            cache_found=True,
            run_id=run_id,
        )
    except RuntimeError as exc:
        write_github_output(
            args.github_output,
            artifact_name=args.artifact_name,
            cache_found=False,
        )
        print(f"Cache lookup skipped fallback build will run: {exc}")
        return 0

    print(f"Resolved {args.artifact_name} from workflow run {run_id}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
