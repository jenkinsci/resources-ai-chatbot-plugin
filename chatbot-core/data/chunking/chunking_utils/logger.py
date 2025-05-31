"""Logger configuration for chunking scripts."""

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [CHUNKING] [%(levelname)s] [%(filename)s]: %(message)s',
    datefmt='%H:%M:%S'
)

def get_logger():
    """
    Returns a logger instance 
    """
    return logging.getLogger()
