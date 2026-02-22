"""Build the golden QA dataset used by the LLM-as-a-judge pipeline."""

# pylint: disable=line-too-long

from __future__ import annotations

import csv
import json
from pathlib import Path

DATASET_DIR = Path(__file__).resolve().parent / "dataset"
JSONL_PATH = DATASET_DIR / "golden_qa_dataset.jsonl"
CSV_PATH = DATASET_DIR / "golden_qa_dataset.csv"


def _core_samples() -> list[dict[str, str]]:
    """Return curated Jenkins-core question/answer samples."""
    rows = [
        ("What is the difference between a Jenkins controller and agent?",
         "The controller manages jobs, scheduling, and configuration, while agents execute build steps on allocated nodes."),
        ("What is a Jenkinsfile?",
         "A Jenkinsfile is a text file in source control that defines a Pipeline as code."),
        ("When should I use Declarative Pipeline instead of Scripted Pipeline?",
         "Declarative Pipeline is preferred for readability and guardrails, while Scripted Pipeline is used when advanced Groovy control flow is required."),
        ("What is a stage in a Jenkins Pipeline?",
         "A stage is a logical phase of the pipeline, such as build, test, or deploy, used to organize and visualize execution."),
        ("How does the post section work in Declarative Pipeline?",
         "The post section runs conditionally after stages, for example always, success, failure, unstable, or cleanup."),
        ("How do I avoid hardcoding secrets in Jenkins pipelines?",
         "Store secrets in Jenkins Credentials and access them with credentials binding steps instead of writing secrets directly in code."),
        ("What is the purpose of the environment directive in Declarative Pipeline?",
         "The environment directive defines environment variables that are available to steps in the pipeline or a specific stage."),
        ("How can I run the same pipeline on different platforms?",
         "Use matrix or parallel stages with agent labels so each branch runs on the platform-specific node."),
        ("What does disableConcurrentBuilds do in a pipeline?",
         "disableConcurrentBuilds prevents multiple runs of the same job from executing at the same time."),
        ("How do I set a timeout for an entire pipeline run?",
         "Use options { timeout(...) } in Declarative Pipeline, or the timeout step in Scripted blocks."),
        ("What does retry do in Jenkins pipeline scripts?",
         "retry reruns a failing block a defined number of times to handle transient failures."),
        ("What is stash and unstash used for?",
         "stash stores small workspace files for later pipeline stages, and unstash restores them on another node or stage."),
        ("How do I pass build parameters to a Jenkins pipeline job?",
         "Define parameters in the job or Jenkinsfile, then read them from the params object during execution."),
        ("What is a multibranch pipeline job?",
         "A multibranch pipeline automatically discovers branches and pull requests and runs each using its branch Jenkinsfile."),
        ("How do webhooks help Jenkins jobs start faster?",
         "Webhooks push events from the SCM provider to Jenkins immediately, avoiding slow polling intervals."),
        ("What does archiveArtifacts do?",
         "archiveArtifacts stores selected files from the workspace as build artifacts for later download or traceability."),
        ("How do I publish test results in Jenkins pipeline?",
         "Use junit or related publishers to collect test reports and show pass/fail trends in Jenkins."),
        ("What is a shared library in Jenkins?",
         "A shared library centralizes reusable pipeline functions and classes so teams avoid copy-pasting Jenkinsfile logic."),
        ("How do I control where a stage runs?",
         "Set agent labels or agent directives so Jenkins schedules the stage on matching nodes."),
        ("What is the purpose of buildDiscarder?",
         "buildDiscarder limits old builds and artifacts retention to control disk usage."),
        ("What does input step do in pipeline?",
         "The input step pauses pipeline execution and waits for manual approval or parameter input."),
        ("How do I trigger one job from another in Jenkins?",
         "Use build steps or pipeline build job calls to start downstream jobs with optional parameters."),
        ("Why use fingerprints in Jenkins?",
         "Fingerprints track artifacts across jobs and builds so you can trace where files were produced and consumed."),
        ("How can I run steps only on the main branch?",
         "Use when conditions in Declarative Pipeline, such as when { branch 'main' }, to gate stage execution."),
        ("What does skipDefaultCheckout do?",
         "skipDefaultCheckout disables automatic SCM checkout so the pipeline can perform custom checkout behavior."),
        ("How do I clean workspace before or after builds?",
         "Use workspace cleanup patterns or explicit delete steps to remove previous build files and avoid contamination."),
        ("What is quiet down mode in Jenkins?",
         "Quiet down stops new builds from starting while allowing running builds to finish, useful before maintenance."),
        ("What is safe restart in Jenkins?",
         "Safe restart restarts Jenkins after active builds complete, reducing disruption."),
        ("How can I protect Jenkins with role-based permissions?",
         "Use authorization strategy plugins to assign permissions to groups and limit admin rights to trusted users."),
        ("What does node block mean in Scripted Pipeline?",
         "A node block allocates an executor and workspace on a matching agent for the enclosed steps."),
        ("How do I schedule builds with cron in Jenkins?",
         "Configure cron expressions in build triggers or pipeline triggers so jobs run on schedule."),
        ("What is the purpose of workspace in Jenkins?",
         "Workspace is the directory where Jenkins checks out source code and executes build steps."),
        ("How do I prevent SCM credentials from leaking in logs?",
         "Use credentials masking and avoid echoing secret variables directly in shell commands."),
        ("How should I store Jenkins configuration for repeatable setup?",
         "Use configuration as code and source-controlled job definitions to make setup reproducible."),
        ("What does currentBuild.result control?",
         "currentBuild.result sets or reads build status, such as SUCCESS, UNSTABLE, or FAILURE."),
        ("How do I make pipeline logs easier to read?",
         "Use clear stage names, concise shell output, and log formatting plugins like timestamps and ANSI color."),
    ]
    return [
        {
            "category": "core",
            "question": question,
            "ground_truth": answer,
            "reference_context": answer,
        }
        for question, answer in rows
    ]


def _plugin_samples() -> list[dict[str, str]]:
    """Return plugin-oriented question/answer samples."""
    plugin_specs = [
        ("Git plugin", "integrates Jenkins with Git repositories for checkout and polling"),
        ("GitHub plugin", "integrates Jenkins with GitHub metadata, webhooks, and status reporting"),
        ("GitLab plugin", "integrates Jenkins with GitLab webhooks and commit status updates"),
        ("Slack Notification plugin", "sends Jenkins build notifications to Slack channels"),
        ("Email Extension plugin", "adds flexible email notifications and templates for build results"),
        ("Docker plugin", "allows Jenkins to start ephemeral agents in Docker environments"),
        ("Kubernetes plugin", "provisions Jenkins agents as Kubernetes pods on demand"),
        ("Job DSL plugin", "generates Jenkins jobs from Groovy DSL scripts"),
        ("Configuration as Code plugin", "defines Jenkins global configuration through YAML files"),
        ("Blue Ocean plugin", "provides a modern pipeline visualization and editing interface"),
        ("Matrix Authorization Strategy plugin", "enables matrix-based permission assignment"),
        ("Role-based Authorization Strategy plugin", "adds role-based access control for global and item permissions"),
        ("Warnings Next Generation plugin", "aggregates static analysis findings and trends"),
        ("JUnit plugin", "publishes JUnit-compatible test results in Jenkins"),
        ("SSH Build Agents plugin", "connects and manages agents over SSH"),
        ("Copy Artifact plugin", "copies artifacts from one job build to another"),
        ("Build Timeout plugin", "enforces timeout policies for freestyle jobs and wrappers"),
        ("Workspace Cleanup plugin", "removes workspace files using configurable cleanup rules"),
        ("AnsiColor plugin", "renders ANSI color codes in Jenkins console output"),
        ("Timestamper plugin", "adds timestamps to build console logs"),
    ]

    samples: list[dict[str, str]] = []
    for plugin_name, purpose in plugin_specs:
        answer_purpose = (
            f"The {plugin_name} {purpose}. It is typically installed from Manage Jenkins > Plugins."
        )
        answer_setup = (
            f"After installing the {plugin_name}, configure it in Manage Jenkins settings or the job "
            "configuration, then reference it from your pipeline or freestyle job as needed."
        )
        samples.append(
            {
                "category": "plugins",
                "question": f"What is the main purpose of the {plugin_name} in Jenkins?",
                "ground_truth": answer_purpose,
                "reference_context": answer_purpose,
            }
        )
        samples.append(
            {
                "category": "plugins",
                "question": f"What are the first setup steps for the {plugin_name}?",
                "ground_truth": answer_setup,
                "reference_context": answer_setup,
            }
        )
    return samples


def _error_samples() -> list[dict[str, str]]:
    """Return troubleshooting-oriented question/answer samples."""
    rows = [
        ("How should I handle 'No such DSL method' errors in a Jenkins pipeline?",
         "This error usually means the step name is wrong or a required plugin is missing. Verify spelling and confirm the plugin providing the step is installed."),
        ("What does 'script not yet approved' mean in Jenkins?",
         "It means script security blocked unapproved Groovy. An administrator must approve the signature or refactor to approved pipeline steps."),
        ("How do I troubleshoot 'Permission denied' in Jenkins workspace?",
         "Check filesystem ownership and agent user permissions on the workspace path, then retry after correcting access rights."),
        ("What causes 'Agent is offline' build failures?",
         "Jenkins cannot schedule steps because the selected node is disconnected, busy, or misconfigured. Restore connectivity or adjust labels."),
        ("How do I fix Git checkout authentication failures in Jenkins?",
         "Validate repository credentials in Jenkins, ensure correct credential binding in the job, and verify SCM URL and access rights."),
        ("What should I check when Jenkins says 'No space left on device'?",
         "Free disk space on controller or agent, clean old builds/artifacts, and configure retention to prevent repeated disk exhaustion."),
        ("How do I investigate plugin dependency errors after upgrade?",
         "Review plugin manager dependency warnings, upgrade dependent plugins together, and avoid partial incompatible version sets."),
        ("Why does Jenkins fail with Java version mismatch errors?",
         "The runtime or build tools require a different Java version. Align controller, agent, and toolchain Java versions."),
        ("How can I debug timeout failures in pipeline stages?",
         "Identify long-running steps in logs, tune timeout values, and optimize or split expensive operations."),
        ("What should I do when tests are not discovered by Jenkins?",
         "Confirm test report paths match produced files and that the test publisher step runs after report generation."),
        ("How do I troubleshoot 'Host key verification failed' in Jenkins Git steps?",
         "Configure known hosts or SSH host key verification strategy correctly for the Git server."),
        ("What does 'Cannot connect to Docker daemon' mean in Jenkins jobs?",
         "The job cannot access Docker socket or daemon endpoint. Check daemon availability, permissions, and environment configuration."),
        ("How do I fix pipeline failures caused by missing credentials IDs?",
         "Create the credentials with the expected ID or update pipeline configuration to use an existing credential ID."),
        ("What causes Jenkins webhook builds not to trigger?",
         "Webhook URL, secret, or SCM event settings are wrong. Verify endpoint reachability and payload configuration."),
        ("How do I investigate random network-related build failures?",
         "Check external service availability, retry policies, DNS resolution, and proxy/firewall rules affecting agents."),
        ("What does an unstable build status usually indicate?",
         "The build completed but quality gates or tests reported issues, so status is UNSTABLE rather than FAILURE."),
        ("How do I fix 'No such file or directory' in Jenkins shell steps?",
         "Ensure expected files exist in workspace, validate relative paths, and confirm checkout/build steps ran successfully."),
        ("What should I check when Jenkins cannot archive artifacts?",
         "Verify artifact patterns match actual files and that artifacts are produced before archive step executes."),
        ("How can I address flaky test failures in CI pipelines?",
         "Track flaky tests, add retries selectively, and improve test isolation rather than masking persistent failures."),
        ("How do I diagnose why a stage is skipped unexpectedly?",
         "Inspect when conditions, branch filters, and environment variables controlling stage execution."),
        ("What causes SCM polling to miss repository changes?",
         "Polling credentials or repository settings may be incorrect; webhooks are generally more reliable for timely triggers."),
        ("How do I troubleshoot long queue times in Jenkins?",
         "Check executor availability, node labels, resource contention, and throttling settings that delay scheduling."),
        ("How do I debug intermittent agent disconnections?",
         "Review agent logs, network stability, JVM memory, and remoting configuration for recurring disconnect patterns."),
        ("What should I do if Jenkins startup fails after plugin changes?",
         "Inspect startup logs for failing plugin classes, disable problematic plugin versions, and restart with compatible set."),
        ("How can I recover from corrupted Jenkins update center metadata?",
         "Clear stale update center data and refresh plugin metadata from a healthy mirror or default source."),
        ("What does 'RejectedAccessException' mean in pipeline logs?",
         "Pipeline attempted a sandbox-restricted method. Use approved steps or request script approval where appropriate."),
        ("How do I handle credential masking not working as expected?",
         "Use withCredentials or equivalent bindings, avoid command echo of secrets, and confirm masking plugins are active."),
        ("What should I check for failing parallel stages?",
         "Inspect each branch logs independently and ensure shared resources are synchronized or isolated."),
        ("How do I troubleshoot artifacts copied from wrong upstream build?",
         "Set explicit build selectors in copy-artifact configuration instead of broad latest-success defaults."),
        ("What does 'upstream trigger did not run' usually mean?",
         "Downstream trigger conditions were not met or permissions prevent trigger execution between jobs."),
    ]
    return [
        {
            "category": "errors",
            "question": question,
            "ground_truth": answer,
            "reference_context": answer,
        }
        for question, answer in rows
    ]


def build_rows() -> list[dict[str, str]]:
    """Build and return all rows with deterministic IDs."""
    rows = _core_samples() + _plugin_samples() + _error_samples()
    output: list[dict[str, str]] = []
    counters = {"core": 0, "plugins": 0, "errors": 0}
    for row in rows:
        category = row["category"]
        counters[category] += 1
        output.append(
            {
                "id": f"{category}-{counters[category]:03d}",
                **row,
            }
        )
    return output


def write_jsonl(rows: list[dict[str, str]], path: Path) -> None:
    """Write rows to JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        for row in rows:
            file_obj.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    """Write rows to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["id", "category", "question", "ground_truth", "reference_context"]
    with path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    """Build and save the golden dataset artifacts."""
    rows = build_rows()
    write_jsonl(rows, JSONL_PATH)
    write_csv(rows, CSV_PATH)
    print(f"Generated {len(rows)} rows.")
    print(f"JSONL: {JSONL_PATH}")
    print(f"CSV:   {CSV_PATH}")


if __name__ == "__main__":
    main()
