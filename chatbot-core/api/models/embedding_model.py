"""Loads and exports once the sentence transformer model."""

from rag.embedding.embedding_utils import load_embedding_model
from api.config.loader import CONFIG
from utils import LoggerFactory

logger = LoggerFactory.instance().get_logger("api")

EMBEDDING_MODEL = load_embedding_model(CONFIG["retrieval"]["embedding_model_name"], logger)
