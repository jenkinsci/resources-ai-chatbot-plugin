"""Unit tests for the shared logger factory."""

import logging
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from utils.logger import LoggerFactory


@pytest.fixture(name="logger_lookup", autouse=True)
def isolate_logger_factory(monkeypatch):
    """Use standalone loggers without modifying the global logger registry."""
    loggers = {}
    monkeypatch.setattr(LoggerFactory, "_loggers", loggers)
    lookup = Mock(side_effect=logging.Logger)
    monkeypatch.setattr("utils.logger.logging", SimpleNamespace(
        getLogger=lookup, INFO=logging.INFO,
        StreamHandler=logging.StreamHandler, Formatter=logging.Formatter,
    ))

    yield lookup

    for logger in loggers.values():
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()


def test_get_logger_creates_uppercase_info_logger():
    """New loggers use the normalized name and expected level."""
    logger = LoggerFactory.get_logger("chat_service")

    assert isinstance(logger, logging.Logger)
    assert logger.name == "CHAT_SERVICE"
    assert logger.level == logging.INFO


@pytest.mark.parametrize("second_name", ["chat_service", "CHAT_SERVICE"])
def test_get_logger_reuses_logger_regardless_of_name_case(logger_lookup, second_name):
    """Equivalent names return the same cached logger instance."""
    first_logger = LoggerFactory.get_logger("chat_service")
    second_logger = LoggerFactory.get_logger(second_name)

    assert second_logger is first_logger
    logger_lookup.assert_called_once_with("CHAT_SERVICE")


def test_different_names_return_different_loggers():
    """The cache keeps distinct names separate."""
    assert LoggerFactory.get_logger("first") is not LoggerFactory.get_logger("second")


def test_configure_logger_adds_only_one_stream_handler():
    """Repeated configuration does not attach duplicate handlers."""
    logger = LoggerFactory.get_logger("handler_test")
    original_handler = logger.handlers[0]
    LoggerFactory._configure_logger(logger)  # pylint: disable=protected-access

    assert logger.handlers == [original_handler]
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert logger.propagate is False


def test_configure_logger_uses_factory_formatter_template():
    """Rendered records include the time, name, level, filename and message."""
    logger = LoggerFactory.get_logger("formatter_test")
    formatter = logger.handlers[0].formatter

    assert formatter is not None
    assert formatter.datefmt == "%H:%M:%S"
    record = logging.LogRecord("FORMATTER_TEST", logging.INFO, "example.py", 1,
                               "Hello %s", ("Jenkins",), None)
    # Fix the timestamp conversion so this assertion is independent of timezone.
    formatter.converter = lambda _: (2026, 1, 2, 3, 4, 5, 4, 2, 0)
    assert formatter.format(record) == (
        "03:04:05 [FORMATTER_TEST] [INFO] [example.py]: Hello Jenkins"
    )


def test_instance_returns_logger_factory():
    """The convenience constructor returns a LoggerFactory instance."""
    assert isinstance(LoggerFactory.instance(), LoggerFactory)
