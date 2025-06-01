"""Logger configuration for chatbot-core."""

import logging

class LoggerFactory:
    """
    A factory class for creating and managing named loggers with consistent configuration.

    Ensures that loggers are only configured once and reused across the application.
    """
    _loggers = {}
    _formatter_template = '%(asctime)s [%(name)s] [%(levelname)s] [%(filename)s]: %(message)s'

    @classmethod
    def get_logger(cls, name: str):
        """
        Get a logger instance with the specified name.

        If a logger with the given name already exists, it is returned.
        Otherwise, a new logger is created, configured, and returned.

        Args:
            name (str): The name of the logger.

        Returns:
            logging.Logger: The configured logger instance.
        """
        name = name.upper()
        if name in cls._loggers:
            return cls._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)

        cls._configure_logger(logger)
        cls._loggers[name] = logger
        return logger

    @classmethod
    def _configure_logger(cls, logger: logging.Logger):
        """
        Configure the provided logger with a StreamHandler and custom formatter.

        Ensures handlers are only attached once to avoid duplicate logs.

        Args:
            logger (logging.Logger): The logger instance to configure.
        """
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(cls._formatter_template, datefmt='%H:%M:%S')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.propagate = False

    @classmethod
    def instance(cls):
        """
        Return an instance of the LoggerFactory.

        Returns:
            LoggerFactory: A new instance of the LoggerFactory class.
        """
        return cls()
