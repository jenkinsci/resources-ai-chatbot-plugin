"""Global configuration and plugins for the pytest suite."""

pytest_plugins = [
    "tests.integration.mocks",
    "tests.unit.mocks.test_env"
]
