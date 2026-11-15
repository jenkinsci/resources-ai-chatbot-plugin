"""
Syntax validator and analyzer for Jenkins Declarative and Scripted Pipelines.
"""

from dataclasses import dataclass, field
import re
from typing import List, Tuple, Optional


ALLOWED_TOP_LEVEL_DIRECTIVES = frozenset({
    "agent",
    "environment",
    "options",
    "parameters",
    "triggers",
    "stage",
    "stages",
    "tools",
    "post",
})

ALLOWED_POST_CONDITIONS = frozenset({
    "always",
    "changed",
    "fixed",
    "regression",
    "aborted",
    "failure",
    "success",
    "unstable",
    "unsuccessful",
    "cleanup",
})

COMMON_STEP_COMMANDS = frozenset({
    "sh",
    "bat",
    "powershell",
    "pwsh",
    "echo",
    "checkout",
    "git",
    "archiveArtifacts",
    "junit",
    "publishHTML",
    "mail",
    "slackSend",
    "sleep",
    "timeout",
    "retry",
    "withCredentials",
    "withEnv",
    "script",
})


@dataclass
class PipelineValidationResult:
    """Structured validation outcome for a Jenkins pipeline script."""

    is_valid: bool
    pipeline_type: str  # "declarative", "scripted", or "unknown"
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    stages: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert validation result to dictionary representation."""
        return {
            "is_valid": self.is_valid,
            "pipeline_type": self.pipeline_type,
            "errors": self.errors,
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "stages": self.stages,
        }


def strip_comments_and_strings(content: str) -> str:
    """
    Remove comments and strings while preserving whitespace and newlines,
    preventing quotes or comments from throwing off brace counting.
    """
    # Regex pattern to match comments and single/double/triple quotes
    pattern = re.compile(
        r"""
        (//[^\n]*)                    # Single-line comment
        | (/\*[\s\S]*?\*/)            # Multi-line comment
        | ('''[\s\S]*?''')            # Triple single-quoted string
        | (\"\"\"[\s\S]*?\"\"\")      # Triple double-quoted string
        | ('(?:\\.|[^'\\])*')         # Single-quoted string
        | ("(?:\\.|[^"\\])*")         # Double-quoted string
        """,
        re.VERBOSE,
    )

    def replace_match(match: re.Match) -> str:
        matched_text = match.group(0)
        # Preserve newlines so line numbers remain identical
        return "".join("\n" if char == "\n" else " " for char in matched_text)

    return pattern.sub(replace_match, content)


def check_brace_balance(content: str) -> Tuple[bool, Optional[str]]:
    """
    Check whether opening and closing braces { } are properly balanced.
    Returns (is_balanced, error_message).
    """
    stripped = strip_comments_and_strings(content)
    stack: List[Tuple[int, int]] = []  # (line_no, col_no)
    line_no = 1
    col_no = 1

    for char in stripped:
        if char == "\n":
            line_no += 1
            col_no = 1
            continue

        if char == "{":
            stack.append((line_no, col_no))
        elif char == "}":
            if not stack:
                return (
                    False,
                    f"Unexpected closing brace '}}' at line {line_no}, col {col_no}.",
                )
            stack.pop()

        col_no += 1

    if stack:
        unclosed_line, unclosed_col = stack[-1]
        return (
            False,
            f"Unclosed brace '{{' from line {unclosed_line}, col {unclosed_col}.",
        )

    return True, None


def extract_stage_names(content: str) -> List[str]:
    """Extract list of stage names from pipeline definition."""
    pattern = re.compile(
        r"""\bstage\s*\(\s*['"]([^'"]+)['"]\s*\)""", re.IGNORECASE
    )
    return [match.group(1) for match in pattern.finditer(content)]


def extract_stage_blocks(
    raw_content: str, stripped_content: str
) -> List[Tuple[str, str]]:
    """
    Extract each stage name and its raw body content using balanced brace matching.
    """
    stages: List[Tuple[str, str]] = []
    pattern = re.compile(
        r"""\bstage\s*\(\s*['"]([^'"]+)['"]\s*\)\s*\{""", re.IGNORECASE
    )

    for match in pattern.finditer(raw_content):
        stage_name = match.group(1)
        open_brace_idx = match.end() - 1

        depth = 0
        end_brace_idx = -1
        for idx in range(open_brace_idx, len(stripped_content)):
            if stripped_content[idx] == "{":
                depth += 1
            elif stripped_content[idx] == "}":
                depth -= 1
                if depth == 0:
                    end_brace_idx = idx
                    break

        if end_brace_idx != -1:
            stage_body = raw_content[open_brace_idx + 1:end_brace_idx]
            stages.append((stage_name, stage_body))

    return stages


def _validate_agent(stripped_content: str, errors: List[str], suggestions: List[str]):
    """Verify required agent directive is present."""
    agent_match = re.search(r"\bagent\s+([A-Za-z0-9_]+|\{)", stripped_content)
    if not agent_match:
        errors.append(
            "Missing required 'agent' directive. Declarative Pipelines "
            "require an 'agent' section (e.g. 'agent any' or 'agent none')."
        )
    else:
        agent_type = agent_match.group(1).strip()
        if agent_type not in ("any", "none", "{"):
            suggestions.append(
                f"Agent is set to '{agent_type}'. Ensure this matches "
                "an active agent label or container template."
            )


def _validate_stages(
    raw_content: str,
    stripped_content: str,
    errors: List[str],
    warnings: List[str],
) -> List[str]:
    """Verify stages block and stage contents."""
    stages_match = re.search(r"\bstages\s*\{", stripped_content)
    if not stages_match:
        errors.append(
            "Missing required 'stages' block. Declarative Pipelines must "
            "contain a 'stages { ... }' block."
        )

    stage_names = extract_stage_names(raw_content)
    if stages_match and not stage_names:
        errors.append(
            "The 'stages' block must contain at least one stage "
            "(e.g., stage('Build') { steps { ... } })."
        )

    stage_blocks = extract_stage_blocks(raw_content, stripped_content)
    for stage_name, stage_body in stage_blocks:
        body_stripped = strip_comments_and_strings(stage_body)
        has_steps = bool(re.search(r"\bsteps\s*\{", body_stripped))
        has_parallel = bool(re.search(r"\bparallel\s*\{", body_stripped))
        has_nested = bool(re.search(r"\bstages\s*\{", body_stripped))
        has_matrix = bool(re.search(r"\bmatrix\s*\{", body_stripped))

        if not (has_steps or has_parallel or has_nested or has_matrix):
            found_steps = [
                cmd for cmd in COMMON_STEP_COMMANDS
                if re.search(rf"\b{cmd}\b", body_stripped)
            ]
            if found_steps:
                errors.append(
                    f"Stage '{stage_name}' contains direct step commands "
                    f"({', '.join(found_steps[:3])}) without a 'steps {{ ... }}' block."
                )
            else:
                warnings.append(
                    f"Stage '{stage_name}' is missing a 'steps {{ ... }}' block."
                )

    return stage_names


def _validate_post_section(
    raw_content: str,
    stripped_content: str,
    warnings: List[str],
    suggestions: List[str],
):
    """Verify optional post block conditions."""
    post_pattern = re.compile(r"\bpost\s*\{", re.IGNORECASE)
    has_post = False

    for post_match in post_pattern.finditer(raw_content):
        has_post = True
        open_brace = post_match.end() - 1
        depth = 0
        end_brace = -1
        for idx in range(open_brace, len(stripped_content)):
            if stripped_content[idx] == "{":
                depth += 1
            elif stripped_content[idx] == "}":
                depth -= 1
                if depth == 0:
                    end_brace = idx
                    break

        if end_brace != -1:
            post_body = stripped_content[open_brace + 1:end_brace]
            condition_matches = re.findall(r"([A-Za-z0-9_]+)\s*\{", post_body)
            for cond in condition_matches:
                if cond not in ALLOWED_POST_CONDITIONS:
                    allowed_str = ", ".join(sorted(ALLOWED_POST_CONDITIONS))
                    warnings.append(
                        f"Unknown post-condition '{cond}'. "
                        f"Standard conditions are: {allowed_str}"
                    )

    if not has_post:
        suggestions.append(
            "Consider adding a 'post { failure { ... } }' block to clean up "
            "workspace or notify team on failures."
        )


def validate_declarative_pipeline(
    raw_content: str, stripped_content: str
) -> PipelineValidationResult:
    """Validate a Jenkins Declarative Pipeline against official syntax rules."""
    errors: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []

    is_balanced, brace_error = check_brace_balance(raw_content)
    if not is_balanced:
        errors.append(brace_error or "Syntax error: Unbalanced braces in pipeline.")
        return PipelineValidationResult(
            is_valid=False,
            pipeline_type="declarative",
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            stages=extract_stage_names(raw_content),
        )

    _validate_agent(stripped_content, errors, suggestions)
    stage_names = _validate_stages(raw_content, stripped_content, errors, warnings)
    _validate_post_section(raw_content, stripped_content, warnings, suggestions)

    return PipelineValidationResult(
        is_valid=len(errors) == 0,
        pipeline_type="declarative",
        errors=errors,
        warnings=warnings,
        suggestions=suggestions,
        stages=stage_names,
    )


def validate_pipeline_syntax(pipeline_script: str) -> PipelineValidationResult:
    """
    Inspect and validate a Jenkins pipeline script.

    Args:
        pipeline_script (str): Full text of the Jenkinsfile / pipeline script.

    Returns:
        PipelineValidationResult: Structured validation report.
    """
    if not pipeline_script or not pipeline_script.strip():
        return PipelineValidationResult(
            is_valid=False,
            pipeline_type="unknown",
            errors=["Pipeline script is empty."],
            warnings=[],
            suggestions=[
                "Provide a valid Declarative Pipeline starting with 'pipeline { ... }'."
            ],
            stages=[],
        )

    stripped = strip_comments_and_strings(pipeline_script)

    if re.search(r"\bpipeline\s*\{", stripped):
        return validate_declarative_pipeline(pipeline_script, stripped)

    if re.search(r"\bnode\s*(\(|\{)", stripped):
        is_balanced, brace_error = check_brace_balance(pipeline_script)
        errors = [brace_error] if not is_balanced else []
        stages = extract_stage_names(pipeline_script)
        suggestions = [
            "This script is written in Jenkins Scripted Pipeline syntax (node { ... }).",
            "Declarative Pipeline syntax (pipeline { ... }) is recommended for modern Jenkins.",
        ]
        return PipelineValidationResult(
            is_valid=is_balanced,
            pipeline_type="scripted",
            errors=errors,
            warnings=["Scripted pipelines are less strictly constrained than Declarative."],
            suggestions=suggestions,
            stages=stages,
        )

    return PipelineValidationResult(
        is_valid=False,
        pipeline_type="unknown",
        errors=[
            "Not a recognizable Jenkins pipeline. "
            "Expected 'pipeline { ... }' or 'node { ... }'."
        ],
        warnings=[],
        suggestions=[
            "Start your declarative pipeline with "
            "'pipeline { agent any ... stages { ... } }'."
        ],
        stages=[],
    )
