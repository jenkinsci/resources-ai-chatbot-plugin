"""
Unit tests for Jenkins Pipeline syntax validator.
"""

# pylint: disable=missing-function-docstring,duplicate-code

from api.tools.pipeline_validator import (
    validate_pipeline_syntax,
    check_brace_balance,
    strip_comments_and_strings,
    extract_stage_names,
    extract_stage_blocks,
    PipelineValidationResult,
)


class TestStripCommentsAndStrings:
    """Tests for stripping comments and strings while preserving structure."""

    def test_strip_line_comments(self):
        code = "pipeline {\n// this is a comment with { braces }\nagent any\n}"
        stripped = strip_comments_and_strings(code)
        assert "this is a comment" not in stripped
        assert "{" in stripped  # Only the pipeline brace remains

    def test_strip_block_comments(self):
        code = "pipeline {\n/* block comment { with brace } */\nagent any\n}"
        stripped = strip_comments_and_strings(code)
        assert "block comment" not in stripped

    def test_strip_quoted_strings(self):
        code = 'stage("Build with { braces }") { steps { echo \'hello { world }\' } }'
        stripped = strip_comments_and_strings(code)
        assert "Build with" not in stripped
        assert "hello" not in stripped

    def test_strip_triple_quoted_strings(self):
        code = "sh '''multi line\nstring with { braces }\n'''"
        stripped = strip_comments_and_strings(code)
        assert "multi line" not in stripped


class TestCheckBraceBalance:
    """Tests for checking curly brace matching."""

    def test_balanced_braces(self):
        code = "pipeline { agent any stages { stage('Build') { steps { echo 'ok' } } } }"
        is_balanced, error = check_brace_balance(code)
        assert is_balanced is True
        assert error is None

    def test_unclosed_brace(self):
        code = "pipeline { agent any stages { stage('Build') { steps { echo 'ok' } }"
        is_balanced, error = check_brace_balance(code)
        assert is_balanced is False
        assert "Unclosed brace '{'" in error

    def test_unexpected_closing_brace(self):
        code = "pipeline { agent any } }"
        is_balanced, error = check_brace_balance(code)
        assert is_balanced is False
        assert "Unexpected closing brace '}'" in error

    def test_braces_in_strings_ignored(self):
        code = "echo '{' \n echo '}'"
        is_balanced, _ = check_brace_balance(code)
        assert is_balanced is True


class TestExtractStages:
    """Tests for stage name and block extraction."""

    def test_extract_stage_names(self):
        code = """
        pipeline {
            agent any
            stages {
                stage('Checkout') { steps { checkout scm } }
                stage('Build') { steps { sh 'mvn compile' } }
                stage('Deploy') { steps { sh 'deploy.sh' } }
            }
        }
        """
        stages = extract_stage_names(code)
        assert stages == ["Checkout", "Build", "Deploy"]

    def test_extract_stage_blocks(self):
        code = """
        pipeline {
            agent any
            stages {
                stage('Build') {
                    steps {
                        sh 'mvn install'
                    }
                }
            }
        }
        """
        stripped = strip_comments_and_strings(code)
        blocks = extract_stage_blocks(code, stripped)
        assert len(blocks) == 1
        name, body = blocks[0]
        assert name == "Build"
        assert "mvn install" in body


class TestValidatePipelineSyntax:
    """Tests for the full validate_pipeline_syntax entrypoint."""

    def test_empty_pipeline(self):
        res = validate_pipeline_syntax("")
        assert res.is_valid is False
        assert res.pipeline_type == "unknown"
        assert "empty" in res.errors[0].lower()

    def test_whitespace_pipeline(self):
        res = validate_pipeline_syntax("   \n\t  ")
        assert res.is_valid is False
        assert res.pipeline_type == "unknown"

    def test_valid_declarative_pipeline(self):
        pipeline = """
        pipeline {
            agent any
            stages {
                stage('Build') {
                    steps {
                        sh 'mvn clean package'
                    }
                }
                stage('Test') {
                    steps {
                        junit '**/target/*.xml'
                    }
                }
            }
            post {
                always {
                    cleanWs()
                }
                failure {
                    mail to: 'team@example.com', subject: 'Failed'
                }
            }
        }
        """
        res = validate_pipeline_syntax(pipeline)
        assert res.is_valid is True
        assert res.pipeline_type == "declarative"
        assert len(res.errors) == 0
        assert res.stages == ["Build", "Test"]

    def test_missing_agent_directive(self):
        pipeline = """
        pipeline {
            stages {
                stage('Build') {
                    steps {
                        sh 'echo hello'
                    }
                }
            }
        }
        """
        res = validate_pipeline_syntax(pipeline)
        assert res.is_valid is False
        assert any("missing required 'agent'" in e.lower() for e in res.errors)

    def test_missing_stages_block(self):
        pipeline = """
        pipeline {
            agent any
        }
        """
        res = validate_pipeline_syntax(pipeline)
        assert res.is_valid is False
        assert any("missing required 'stages'" in e.lower() for e in res.errors)

    def test_empty_stages_block(self):
        pipeline = """
        pipeline {
            agent any
            stages {
            }
        }
        """
        res = validate_pipeline_syntax(pipeline)
        assert res.is_valid is False
        assert any("must contain at least one stage" in e.lower() for e in res.errors)

    def test_direct_steps_in_stage_without_steps_block(self):
        pipeline = """
        pipeline {
            agent any
            stages {
                stage('Build') {
                    sh 'mvn clean install'
                }
            }
        }
        """
        res = validate_pipeline_syntax(pipeline)
        assert res.is_valid is False
        assert any("steps { ... }" in e for e in res.errors)

    def test_stage_with_parallel(self):
        pipeline = """
        pipeline {
            agent any
            stages {
                stage('Parallel Test') {
                    parallel {
                        stage('Unit') { steps { echo 'unit' } }
                        stage('Integration') { steps { echo 'integ' } }
                    }
                }
            }
        }
        """
        res = validate_pipeline_syntax(pipeline)
        assert res.is_valid is True

    def test_unknown_post_condition(self):
        pipeline = """
        pipeline {
            agent any
            stages {
                stage('Build') {
                    steps { echo 'hi' }
                }
            }
            post {
                on_error {
                    echo 'bad condition'
                }
            }
        }
        """
        res = validate_pipeline_syntax(pipeline)
        assert res.is_valid is True
        assert any("unknown post-condition 'on_error'" in w.lower() for w in res.warnings)

    def test_scripted_pipeline(self):
        scripted = """
        node('linux') {
            stage('Build') {
                sh 'make'
            }
            stage('Deploy') {
                echo 'done'
            }
        }
        """
        res = validate_pipeline_syntax(scripted)
        assert res.is_valid is True
        assert res.pipeline_type == "scripted"
        assert res.stages == ["Build", "Deploy"]
        assert any("declarative" in s.lower() for s in res.suggestions)

    def test_unbalanced_scripted_pipeline(self):
        scripted = "node { stage('Build') { sh 'make' }"
        res = validate_pipeline_syntax(scripted)
        assert res.is_valid is False
        assert res.pipeline_type == "scripted"
        assert len(res.errors) > 0

    def test_unknown_script_type(self):
        res = validate_pipeline_syntax("print('Hello from Python')")
        assert res.is_valid is False
        assert res.pipeline_type == "unknown"
        assert any("not a recognizable jenkins pipeline" in e.lower() for e in res.errors)

    def test_to_dict_method(self):
        res = PipelineValidationResult(
            is_valid=True,
            pipeline_type="declarative",
            errors=[],
            warnings=[],
            suggestions=["Add post"],
            stages=["Build"],
        )
        d = res.to_dict()
        assert d["is_valid"] is True
        assert d["pipeline_type"] == "declarative"
        assert d["stages"] == ["Build"]
