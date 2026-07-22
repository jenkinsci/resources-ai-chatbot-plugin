"""Resolve the latest successful retrieval vector cache artifact."""

import argparse
import json
import os
from pathlib import Path
from typing import Any
from urllib import parse, request
from urllib.error import HTTPError, URLError

GITHUB_API_URL = "https://api.github.com"
CACHE_BUILD_JOB_NAME = "build-retrieval-cache"


def default_artifact_name() -> str:
    """
    Build the default cache artifact name.

    Returns:
        str: Stable retrieval cache artifact name.
    """
    return "retrieval-vector-database"


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


def list_repository_artifacts(
    repository: str,
    artifact_name: str,
    token: str,
) -> list[dict[str, Any]]:
    """
    List recent repository artifacts matching the retrieval cache artifact name.

    Args:
        repository (str): Repository in OWNER/REPO format.
        artifact_name (str): Artifact name to find.
        token (str): GitHub token with Actions read access.

    Returns:
        list[dict[str, Any]]: Recent repository artifact records.
    """
    query = parse.urlencode({"name": artifact_name, "per_page": 100})
    payload = github_api_get(
        f"/repos/{repository}/actions/artifacts?{query}",
        token,
    )
    artifacts = payload.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise RuntimeError("GitHub API artifacts payload is invalid")
    return [artifact for artifact in artifacts if isinstance(artifact, dict)]


def get_artifact_run_id(artifact: dict[str, Any], artifact_name: str) -> int | None:
    """
    Return the owning workflow run ID for a usable cache artifact.

    Args:
        artifact (dict[str, Any]): Repository artifact payload from GitHub.
        artifact_name (str): Artifact name to find.

    Returns:
        int | None: Owning workflow run ID when the artifact is usable.
    """
    if artifact.get("name") != artifact_name or artifact.get("expired") is not False:
        return None

    workflow_run = artifact.get("workflow_run")
    if not isinstance(workflow_run, dict):
        return None

    run_id = workflow_run.get("id")
    return run_id if isinstance(run_id, int) else None


def has_successful_cache_build_job(
    repository: str,
    run_id: int,
    token: str,
) -> bool:
    """
    Return whether a workflow run completed its retrieval cache build job.

    Args:
        repository (str): Repository in OWNER/REPO format.
        run_id (int): Workflow run ID to inspect.
        token (str): GitHub token with Actions read access.

    Returns:
        bool: True when the retrieval cache build job completed successfully.
    """
    query = parse.urlencode({"filter": "latest", "per_page": 100})
    payload = github_api_get(
        f"/repos/{repository}/actions/runs/{run_id}/jobs?{query}",
        token,
    )
    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list):
        raise RuntimeError("GitHub API workflow jobs payload is invalid")

    for job in jobs:
        if not isinstance(job, dict):
            continue
        job_name = job.get("name")
        if not isinstance(job_name, str):
            continue
        is_cache_build = job_name == CACHE_BUILD_JOB_NAME or job_name.endswith(
            f" / {CACHE_BUILD_JOB_NAME}"
        )
        if (
            is_cache_build
            and job.get("status") == "completed"
            and job.get("conclusion") == "success"
        ):
            return True
    return False


def describe_artifact_skip(artifact: dict[str, Any], artifact_name: str) -> str | None:
    """
    Return the reason a candidate artifact cannot be reused.

    Args:
        artifact (dict[str, Any]): Repository artifact payload from GitHub.
        artifact_name (str): Required artifact name.

    Returns:
        str | None: Skip reason, or None when the artifact is reusable.
    """
    if artifact.get("name") != artifact_name:
        return None
    if artifact.get("expired") is not False:
        return "artifact is expired"
    workflow_run = artifact.get("workflow_run")
    if not isinstance(workflow_run, dict):
        return "artifact is missing workflow run metadata"
    return None


def resolve_run_id(
    repository: str,
    artifact_name: str,
    token: str,
) -> int:
    """
    Resolve the latest successful workflow run containing the cache artifact.

    Args:
        repository (str): Repository in OWNER/REPO format.
        artifact_name (str): Required artifact name.
        token (str): GitHub token with Actions read access.

    Returns:
        int: Workflow run ID that contains the requested artifact.

    Raises:
        RuntimeError: If no valid cache artifact can be found.
    """
    skip_reasons: list[str] = []
    for artifact in list_repository_artifacts(repository, artifact_name, token):
        run_id = get_artifact_run_id(artifact, artifact_name)
        if run_id is None:
            reason = describe_artifact_skip(artifact, artifact_name)
            if reason is not None:
                skip_reasons.append(reason)
            continue
        if has_successful_cache_build_job(repository, run_id, token):
            return run_id
        skip_reasons.append(
            f"run {run_id} has no completed successful {CACHE_BUILD_JOB_NAME} job"
        )

    details = "; ".join(skip_reasons) if skip_reasons else "no matching artifacts found"
    raise RuntimeError(
        f"No reusable '{artifact_name}' artifact found in repository runs: "
        f"{details}. The fallback cache build will run."
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
