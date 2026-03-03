"""Unit tests for LoggerFactory in utils/logger.py (issue #223).

Covers:
- Logger creation and naming
- Singleton/caching behavior
- Name uppercasing
- Handler configuration (no duplicates)
- Formatter template content
- Propagate flag
- instance() factory method
"""

import logging
import pytest
from utils.logger import LoggerFactory


@pytest.fixture(autouse=True)
def reset_logger_factory():
    """Reset LoggerFactory._loggers between tests to ensure isolation."""
    original = LoggerFactory._loggers.copy()
    LoggerFactory._loggers.clear()
    yield
    LoggerFactory._loggers.clear()
    LoggerFactory._loggers.update(original)


class TestGetLogger:
    """Tests for LoggerFactory.get_logger."""

    def test_returns_logger_instance(self):
        logger = LoggerFactory.get_logger("test_module")
        assert isinstance(logger, logging.Logger)

    def test_logger_name_is_uppercased(self):
        logger = LoggerFactory.get_logger("my_service")
        assert logger.name == "MY_SERVICE"

    def test_logger_level_is_info(self):
        logger = LoggerFactory.get_logger("level_check")
        assert logger.level == logging.INFO

    def test_same_name_returns_same_instance(self):
        logger1 = LoggerFactory.get_logger("shared")
        logger2 = LoggerFactory.get_logger("shared")
        assert logger1 is logger2

    def test_same_name_different_case_returns_same_instance(self):
        logger1 = LoggerFactory.get_logger("CasE")
        logger2 = LoggerFactory.get_logger("case")
        assert logger1 is logger2

    def test_different_names_return_different_instances(self):
        logger1 = LoggerFactory.get_logger("alpha")
        logger2 = LoggerFactory.get_logger("beta")
        assert logger1 is not logger2
        assert logger1.name != logger2.name

    def test_logger_cached_in_loggers_dict(self):
        LoggerFactory.get_logger("cached")
        assert "CACHED" in LoggerFactory._loggers


class TestConfigureLogger:
    """Tests for LoggerFactory._configure_logger (via get_logger)."""

    def test_logger_has_exactly_one_handler(self):
        logger = LoggerFactory.get_logger("handler_count")
        assert len(logger.handlers) == 1

    def test_no_duplicate_handlers_on_second_call(self):
        logger = LoggerFactory.get_logger("no_dupe")
        # Manually call _configure_logger again
        LoggerFactory._configure_logger(logger)
        assert len(logger.handlers) == 1

    def test_handler_is_stream_handler(self):
        logger = LoggerFactory.get_logger("stream_type")
        assert isinstance(logger.handlers[0], logging.StreamHandler)

    def test_formatter_contains_required_fields(self):
        logger = LoggerFactory.get_logger("fmt_check")
        handler = logger.handlers[0]
        fmt_string = handler.formatter._fmt
        assert "%(name)s" in fmt_string
        assert "%(levelname)s" in fmt_string
        assert "%(filename)s" in fmt_string
        assert "%(message)s" in fmt_string

    def test_formatter_contains_asctime(self):
        logger = LoggerFactory.get_logger("asctime_check")
        handler = logger.handlers[0]
        fmt_string = handler.formatter._fmt
        assert "%(asctime)s" in fmt_string

    def test_propagate_is_false(self):
        logger = LoggerFactory.get_logger("no_propagate")
        assert logger.propagate is False


class TestInstance:
    """Tests for LoggerFactory.instance() factory method."""

    def test_returns_logger_factory_instance(self):
        inst = LoggerFactory.instance()
        assert isinstance(inst, LoggerFactory)

    def test_instance_can_get_logger(self):
        inst = LoggerFactory.instance()
        logger = inst.get_logger("via_instance")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "VIA_INSTANCE"
