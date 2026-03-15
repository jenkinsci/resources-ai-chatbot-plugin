"""
Utility functions for saving and loading FAISS indices and associated metadata.
Handles persistence and logging for vector search storage.
"""

import os
import pickle
import faiss
from functools import lru_cache
from utils import LoggerFactory

VECTOR_STORE_DIR = os.path.join(os.path.dirname(
    __file__), "..", "..", "data", "embeddings")
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)


def save_faiss_index(index, path, logger):
    """
    Save a FAISS index to the specified path.

    Args:
        index (faiss.Index): The FAISS index to save.
        path (str): File path to save the index.
    """
    try:
        faiss.write_index(index, path)
        logger.info("FAISS index saved to %s", path)
    except (OSError) as e:
        logger.error("Failed to save FAISS index to %s: %s", path, e)


@lru_cache(maxsize=5)
def load_faiss_index(path):
    """
    Load a FAISS index from a specified path.

    Args:
        path (str): File path to load the index from.

    Returns:
        faiss.Index | None: The loaded FAISS index, or None if loading fails.
    """
    logger = LoggerFactory.instance().get_logger("api")
    try:
        logger.info("Loading FAISS index from %s...", path)
        index = faiss.read_index(path)
        logger.info("FAISS index loaded successfully.")
        return index
    except (OSError, FileNotFoundError) as e:
        logger.error(
            "File error while loading FAISS index from %s: %s", path, e)
    return None


def save_metadata(metadata, path, logger):
    """
    Save metadata to a pickle file.

    Args:
        metadata (Any): Metadata object to serialize.
        path (str): File path to save the metadata.
        logger (logging.Logger): Logger for status or error messages.
    """
    try:
        with open(path, "wb") as f:
            pickle.dump(metadata, f)
        logger.info("Metadata saved to %s", path)
    except (OSError, pickle.PickleError) as e:
        logger.error("Failed to save metadata to %s: %s", path, e)


@lru_cache(maxsize=5)
def load_metadata(path):
    """
    Load metadata from a pickle file.

    Args:
        path (str): File path to load the metadata from.
        logger (logging.Logger): Logger for status or error messages.

    Returns:
        Any | None: Loaded metadata, or None if loading fails.
    """
    logger = LoggerFactory.instance().get_logger("api")  # <--- GET LOGGER LOCALLY
    try:
        logger.info("Loading metadata from %s...", path)
        with open(path, "rb") as f:
            metadata = pickle.load(f)
        logger.info("Metadata loaded successfully.")
        return metadata
    except FileNotFoundError as e:
        logger.error("Metadata file not found: %s - %s", path, e)
    except (OSError, pickle.UnpicklingError) as e:
        logger.error("Failed to load metadata from %s - %s", path, e)
    return None
