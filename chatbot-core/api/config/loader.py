"""
YAML-based configuration loader.

Loads config.yml into a dictionary and exposes it as CONFIG.
"""

import os
import yaml

def load_config():
    """
    Loads and parses the config.yml file located in the same directory.

    Returns:
        dict: Parsed configuration values.
    """
    config_path = os.path.join(os.path.dirname(__file__), "config.yml")
    with open(config_path, "r", encoding='utf-8') as f:
        return yaml.safe_load(f)

CONFIG = load_config()
