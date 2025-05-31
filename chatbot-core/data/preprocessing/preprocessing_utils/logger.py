"""Logger configuration for preprocessing scripts."""

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [PREPROCESSING] [%(levelname)s] [%(filename)s]: %(message)s',
    datefmt='%H:%M:%S'
)

def get_logger():
    """
    Returns a logger instance 
    """
    return logging.getLogger()
