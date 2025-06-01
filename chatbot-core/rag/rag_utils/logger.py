"""Logger configuration for RAG scripts."""

import logging

def get_logger(name):
    """
    Returns a logger instance with a custom name label.
    """
    formatter = logging.Formatter(
        fmt=f'%(asctime)s [{name}] [%(levelname)s] [%(filename)s]: %(message)s',
        datefmt='%H:%M:%S'
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        logger.addHandler(handler)

    return logger
