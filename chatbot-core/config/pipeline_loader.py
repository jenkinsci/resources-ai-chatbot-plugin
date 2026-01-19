"""
YAML-based configuration loader for the data pipeline.

Loads data-pipeline.yml into a dictionary and exposes it as PIPELINE_CONFIG.
Supports environment variable overrides and custom config paths.
"""

import os
from copy import deepcopy

import yaml
from utils import LoggerFactory

logger = LoggerFactory.instance().get_logger("data-pipeline")


def load_pipeline_config(config_path=None):
    """
    Loads and parses the data-pipeline.yml file.

    Priority order:
    1. Explicit config_path parameter
    2. DATA_PIPELINE_CONFIG environment variable
    3. Default: chatbot-core/config/data-pipeline.yml

    Args:
        config_path (str, optional): Explicit path to config file.

    Returns:
        dict: Parsed configuration values with all pipeline settings.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        yaml.YAMLError: If the config file is malformed.
    """
    # Determine config path with priority
    if config_path is None:
        config_path = os.environ.get("DATA_PIPELINE_CONFIG")
    
    if config_path is None:
        # Default to data-pipeline.yml in the config directory
        file_dir = os.path.dirname(__file__)
        config_path = os.path.join(file_dir, "data-pipeline.yml")
    
    if not os.path.exists(config_path):
        message = (
            f"Data pipeline config not found at: {config_path}. Please ensure "
            "data-pipeline.yml exists or set DATA_PIPELINE_CONFIG environment variable."
        )
        raise FileNotFoundError(message)
    
    logger.info("Loading data pipeline configuration from: %s", config_path)
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    # Apply environment variable overrides for critical parameters
    config_overridden = _apply_env_overrides(config)

    logger.info("Data pipeline configuration loaded successfully")
    return config_overridden


def _apply_env_overrides(config):
    """
    Apply environment variable overrides to config.

    Supports overriding key parameters via environment variables:
    - CHUNK_SIZE: Override chunking.chunk_size
    - CHUNK_OVERLAP: Override chunking.chunk_overlap
    - EMBEDDING_MODEL: Override embedding.model_name
    - FAISS_N_LIST: Override storage.n_list
    - FAISS_N_PROBE: Override storage.n_probe

    Args:
        config (dict): The base configuration dictionary.

    Returns:
        dict: Configuration with environment overrides applied.
    """
    cfg = deepcopy(config)

    # Chunking overrides
    if os.environ.get("CHUNK_SIZE"):
        try:
            cfg["chunking"]["chunk_size"] = int(os.environ["CHUNK_SIZE"])
            logger.info("Override chunk_size from env: %s", cfg["chunking"]["chunk_size"])
        except ValueError:
            logger.warning("Invalid CHUNK_SIZE env var: %s", os.environ["CHUNK_SIZE"])

    if os.environ.get("CHUNK_OVERLAP"):
        try:
            cfg["chunking"]["chunk_overlap"] = int(os.environ["CHUNK_OVERLAP"])
            logger.info("Override chunk_overlap from env: %s", cfg["chunking"]["chunk_overlap"])
        except ValueError:
            logger.warning("Invalid CHUNK_OVERLAP env var: %s", os.environ["CHUNK_OVERLAP"])

    # Embedding overrides
    if os.environ.get("EMBEDDING_MODEL"):
        cfg["embedding"]["model_name"] = os.environ["EMBEDDING_MODEL"]
        logger.info("Override embedding model from env: %s", cfg["embedding"]["model_name"])

    # Storage/FAISS overrides
    if os.environ.get("FAISS_N_LIST"):
        try:
            cfg["storage"]["n_list"] = int(os.environ["FAISS_N_LIST"])
            logger.info("Override n_list from env: %s", cfg["storage"]["n_list"])
        except ValueError:
            logger.warning("Invalid FAISS_N_LIST env var: %s", os.environ["FAISS_N_LIST"])

    if os.environ.get("FAISS_N_PROBE"):
        try:
            cfg["storage"]["n_probe"] = int(os.environ["FAISS_N_PROBE"])
            logger.info("Override n_probe from env: %s", cfg["storage"]["n_probe"])
        except ValueError:
            logger.warning("Invalid FAISS_N_PROBE env var: %s", os.environ["FAISS_N_PROBE"])

    return cfg


def get_phase_config(config, phase):
    """
    Extract configuration for a specific pipeline phase.

    Args:
        config (dict): Full pipeline configuration.
        phase (str): Phase name ('collection', 'preprocessing', 'chunking', 'embedding', 'storage').

    Returns:
        dict: Configuration for the specified phase.

    Raises:
        KeyError: If the phase doesn't exist in config.
    """
    if phase not in config:
        raise KeyError(f"Phase '{phase}' not found in pipeline config")
    return config[phase]


# Load default configuration on module import
# Can be overridden by calling load_pipeline_config() explicitly with custom path
try:
    PIPELINE_CONFIG = load_pipeline_config()
except FileNotFoundError as e:
    logger.warning("Could not load default pipeline config: %s", e)
    PIPELINE_CONFIG = None
