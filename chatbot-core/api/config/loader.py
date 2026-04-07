"""
YAML-based configuration loader.

Loads config.yml into a dictionary and exposes it as CONFIG.
"""

import os
import yaml
from utils import LoggerFactory

logger = LoggerFactory.instance().get_logger("api")

def load_config():
    """
    Loads and parses the config.yml file located in the same directory.

    Returns:
        dict: Parsed configuration values.
    """
    file_dir = os.path.dirname(__file__)
    config_dev_path = os.path.join(file_dir, "config.yml")
    config_testing_path = os.path.join(file_dir, "config-testing.yml")

    if os.environ.get("PYTEST_VERSION") is not None:
        logger.info("#### Loading test configuration ####")
        config_path = config_testing_path
    else:
        logger.info("#### Loading dev configuration ####")
        config_path = config_dev_path

    with open(config_path, "r", encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config

CONFIG = load_config()
