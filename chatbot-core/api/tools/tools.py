"""
Definition of the tools avaialable to the Agent.
"""

import logging
from functools import wraps
from typing import Optional
from types import MappingProxyType
from api.models.embedding_model import EMBEDDING_MODEL
from api.tools.utils import (
    filter_retrieved_data,
    is_valid_plugin,
    retrieve_documents,
    extract_top_chunks
)
from api.config.loader import CONFIG
# 1. Rename the logger to avoid clashing with the other functions
decorator_logger = logging.getLogger(__name__)

tool_config = CONFIG.get("tools", {})
MAX_TOOL_OUTPUT_LENGTH = tool_config.get("max_tool_output_length", 4000)


def truncate_tool_output(func):
    """Decorator to prevent tool outputs from crashing the LLM context window."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if isinstance(result, str) and len(result) > MAX_TOOL_OUTPUT_LENGTH:
            truncated = result[:MAX_TOOL_OUTPUT_LENGTH]
            # 2. Use lazy formatting instead of f-strings
            decorator_logger.warning(
                "[SECURITY] Tool '%s' output truncated from %d to %d characters.",
                func.__name__,
                len(result),
                MAX_TOOL_OUTPUT_LENGTH
            )
            # 3. Break the long string into two lines
            return (
                f"{truncated}\n\n...[SYSTEM WARNING: Tool output truncated "
                "to prevent context overflow.]"
            )
        return result
    return wrapper


retrieval_config = CONFIG["retrieval"]


def search_plugin_docs(query: str, keywords: str, logger, plugin_name: Optional[str] = None) -> str:
    """
    Search tool for the plugin docs. Exploits both a sparse and dense search, resulting in a 
    hybrid search.

    Args:
        query (str): The user query.
        keywords (str): Keywords extracted from the user query.
        plugin_name (Optional[str]): The refered plugin name in the query (if available).

    Returns:
        str: The result of the research of the plugin search tool.
    """
    source_name = CONFIG["tool_names"]["plugins"]
    data_retrieved_semantic, scores_semantic, data_retrieved_keyword, scores_keyword = (
        retrieve_documents(
            query=query,
            keywords=keywords,
            logger=logger,
            source_name=source_name,
            embedding_model=EMBEDDING_MODEL
        )
    )

    if plugin_name and is_valid_plugin(plugin_name):
        data_retrieved_semantic, data_retrieved_keyword = filter_retrieved_data(
            data_retrieved_semantic,
            data_retrieved_keyword,
            plugin_name
        )

    return extract_top_chunks(
        data_retrieved_semantic,
        scores_semantic,
        data_retrieved_keyword,
        scores_keyword,
        top_k=retrieval_config["top_k_plugins"],
        logger=logger
    )


def search_jenkins_docs(query: str, keywords: str, logger) -> str:
    """
    Search tool for the Jenkins docs. Exploits both a sparse and dense search, resulting in a 
    hybrid search.

    Args:
        query (str): The user query.
        keywords (str): Keywords extracted from the user query.

    Returns:
        str: The result of the research of the docs search tool.
    """
    source_name = CONFIG["tool_names"]["jenkins_docs"]
    data_retrieved_semantic, scores_semantic, data_retrieved_keyword, scores_keyword = (
        retrieve_documents(
            query=query,
            keywords=keywords,
            logger=logger,
            source_name=source_name,
            embedding_model=EMBEDDING_MODEL
        )
    )

    return extract_top_chunks(
        data_retrieved_semantic,
        scores_semantic,
        data_retrieved_keyword,
        scores_keyword,
        top_k=retrieval_config["top_k_docs"],
        logger=logger
    )


def search_stackoverflow_threads(query: str) -> str:
    """
    Stackoverflow Search tool
    """
    if query:
        pass
    return "Nothing relevant"


def search_community_threads(query: str, keywords: str, logger) -> str:
    """
    Search tool for the community discourse threads. Exploits both a sparse and 
    dense search, resulting in a hybrid search. In this case a higher weight is 
    given to the results that come from the semantic search

    Args:
        query (str): The user query.
        keywords (str): Keywords extracted from the user query.

    Returns:
        str: The result of the research of the docs search tool.
    """
    source_name = CONFIG["tool_names"]["community_threads"]
    data_retrieved_semantic, scores_semantic, data_retrieved_keyword, scores_keyword = (
        retrieve_documents(
            query=query,
            keywords=keywords,
            logger=logger,
            source_name=source_name,
            embedding_model=EMBEDDING_MODEL
        )
    )

    return extract_top_chunks(
        data_retrieved_semantic,
        scores_semantic,
        data_retrieved_keyword,
        scores_keyword,
        top_k=retrieval_config["top_k_discourse"],
        logger=logger,
        semantic_weight=0.7
    )


TOOL_REGISTRY = MappingProxyType({
    "search_plugin_docs": truncate_tool_output(search_plugin_docs),
    "search_jenkins_docs": truncate_tool_output(search_jenkins_docs),
    "search_stackoverflow_threads": truncate_tool_output(search_stackoverflow_threads),
    "search_community_threads": truncate_tool_output(search_community_threads),
})
