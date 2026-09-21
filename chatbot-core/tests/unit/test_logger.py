"""Unit tests for the shared logger factory."""

import logging

import pytest

from utils.logger import LoggerFactory


@pytest.fixture(autouse=True)
def isolate_logger_factory(monkeypatch):
    """Keep cached loggers and handlers from leaking between tests."""
    loggers = {}
    monkeypatch.setattr(LoggerFactory, "_loggers", loggers)

    yield

    for logger in loggers.values():
        logger.handlers.clear()
        logger.propagate = True


def test_get_logger_creates_uppercase_info_logger():
    """New loggers use the normalized name and expected level."""
    logger = LoggerFactory.get_logger("chat_service")

    assert isinstance(logger, logging.Logger)
    assert logger.name == "CHAT_SERVICE"
    assert logger.level == logging.INFO


def test_get_logger_reuses_logger_regardless_of_name_case():
    """Equivalent names return the same cached logger instance."""
    first_logger = LoggerFactory.get_logger("chat_service")
    second_logger = LoggerFactory.get_logger("CHAT_SERVICE")

    assert second_logger is first_logger


def test_configure_logger_adds_only_one_stream_handler():
    """Repeated configuration does not attach duplicate handlers."""
    logger = logging.getLogger("LOGGER_FACTORY_HANDLER_TEST")
    logger.handlers.clear()
    configure_logger = getattr(LoggerFactory, "_configure_logger")

    configure_logger(logger)
    configure_logger(logger)

    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert logger.propagate is False
    logger.handlers.clear()
    logger.propagate = True


def test_configure_logger_uses_factory_formatter_template():
    """The stream handler uses the factory's formatter and time format."""
    logger = LoggerFactory.get_logger("formatter_test")
    formatter = logger.handlers[0].formatter

    assert formatter is not None
    assert getattr(formatter, "_fmt") == getattr(LoggerFactory, "_formatter_template")
    assert formatter.datefmt == "%H:%M:%S"


def test_instance_returns_logger_factory():
    """The convenience constructor returns a LoggerFactory instance."""
    assert isinstance(LoggerFactory.instance(), LoggerFactory)
