"""
Utility functions for saving and loading FAISS indices and associated metadata.
Handles persistence and logging for vector search storage.
"""

import os
import pickle
import json
import faiss

VECTOR_STORE_DIR = os.path.join(os.path.dirname(
    __file__), "..", "..", "data", "embeddings")
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
    except OSError as e:
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
        logger.error(
            "File error while loading FAISS index from %s: %s", path, e)
    return None


def save_metadata(metadata, path, logger):
    """
    Save metadata to a secure JSON file (replacing legacy pickle).

    Args:
        metadata (Any): Metadata object to serialize.
        path (str): File path to save the metadata.
        logger (logging.Logger): Logger for status or error messages.
    """
    # Force the path to use .json just in case a legacy caller passes .pkl
    safe_path = path.replace(
        '.pkl', '.json') if path.endswith('.pkl') else path

    try:
        with open(safe_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f)
        logger.info("Metadata securely saved to %s", safe_path)
    except (OSError, TypeError) as e:
        logger.error("Failed to save metadata to %s: %s", safe_path, e)


def load_metadata(path, logger):
    """
    Load metadata from a JSON file, with a one-time legacy fallback for pickle.

    Args:
        path (str): File path to load the metadata from.
        logger (logging.Logger): Logger for status or error messages.

    Returns:
        Any | None: Loaded metadata, or None if loading fails.
    """
    json_path = path.replace(
        '.pkl', '.json') if path.endswith('.pkl') else path
    pkl_path = path.replace(
        '.json', '.pkl') if path.endswith('.json') else path

    try:
        # 1. Prefer the secure JSON file
        if os.path.exists(json_path):
            logger.info("Loading secure JSON metadata from %s...", json_path)
            with open(json_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            logger.info("Metadata loaded successfully.")
            return metadata

        # 2. Fallback to PKL for backward compatibility + loud warning
        if os.path.exists(pkl_path):
            logger.warning(
                "SECURITY WARNING: Loading legacy pickle metadata from %s. "
                "Please rebuild your vector database to generate secure JSON metadata.",
                pkl_path
            )
            with open(pkl_path, "rb") as f:
                metadata = pickle.load(f)
            logger.info("Legacy metadata loaded successfully.")
            return metadata

        # 3. Neither file exists
        logger.error("Metadata file not found at %s or %s",
                     json_path, pkl_path)
        return None

    except (OSError, json.JSONDecodeError, pickle.UnpicklingError) as e:
        logger.error("Failed to load metadata - %s", e)
        return None
