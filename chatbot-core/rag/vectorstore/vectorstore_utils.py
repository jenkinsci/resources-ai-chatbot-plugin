"""
Utility functions for saving and loading FAISS indices and associated metadata.
Handles persistence and logging for vector search storage.
"""

import os
import json
import faiss

VECTOR_STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "embeddings")
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

def save_faiss_index(index, path, logger):
    """
    Save a FAISS index to the specified path.

    Args:
        index (faiss.Index): The FAISS index to save.
        path (str): File path to save the index.
        logger (logging.Logger): Logger for status or error messages.
    """
    try:
        faiss.write_index(index, path)
        logger.info("FAISS index saved to %s", path)
    except (OSError) as e:
        logger.error("Failed to save FAISS index to %s: %s", path, e)

def load_faiss_index(path, logger):
    """
    Load a FAISS index from a specified path.

    Args:
        path (str): File path to load the index from.
        logger (logging.Logger): Logger for status or error messages.

    Returns:
        faiss.Index | None: The loaded FAISS index, or None if loading fails.
    """
    try:
        logger.info("Loading FAISS index from %s...", path)
        index = faiss.read_index(path)
        logger.info("FAISS index loaded successfully.")
        return index
    except (OSError, FileNotFoundError) as e:
        logger.error("File error while loading FAISS index from %s: %s", path, e)
    return None

def save_metadata(metadata, path, logger):
    """
    Save metadata to a JSON file for security and portability.
    Uses JSON instead of pickle to prevent arbitrary code execution.

    Args:
        metadata (dict): Metadata dictionary to serialize.
        path (str): File path to save the metadata.
        logger (logging.Logger): Logger for status or error messages.
    """
    try:
        # Ensure metadata is JSON-serializable (dict/list)
        if not isinstance(metadata, (dict, list)):
            logger.warning("Metadata is not JSON-serializable, converting to dict")
            metadata = {"data": str(metadata)}
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info("Metadata saved to %s", path)
    except (OSError, TypeError) as e:
        logger.error("Failed to save metadata to %s: %s", path, e)

def load_metadata(path, logger):
    """
    Load metadata from a JSON file for security and portability.
    Uses JSON instead of pickle to prevent arbitrary code execution.

    Args:
        path (str): File path to load the metadata from.
        logger (logging.Logger): Logger for status or error messages.

    Returns:
        dict | None: Loaded metadata, or None if loading fails.
    """
    try:
        logger.info("Loading metadata from %s...", path)
        with open(path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        logger.info("Metadata loaded successfully.")
        return metadata
    except FileNotFoundError as e:
        logger.error("Metadata file not found: %s - %s", path, e)
    except (OSError, json.JSONDecodeError) as e:
        logger.error("Failed to load metadata from %s: %s", path, e)
    return None
