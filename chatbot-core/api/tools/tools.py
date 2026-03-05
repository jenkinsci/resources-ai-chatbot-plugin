"""
Definition of the tools avaialable to the Agent.
"""

import re
from typing import Optional
from types import MappingProxyType
import requests
from api.models.embedding_model import EMBEDDING_MODEL
from api.tools.utils import (
    filter_retrieved_data,
    is_valid_plugin,
    retrieve_documents,
    extract_top_chunks
)
from api.config.loader import CONFIG

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

def _strip_html(html: str) -> str:
    """Remove HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", html)


def _format_so_item(item: dict) -> str:
    """Format a single StackOverflow API item into a readable string."""
    body = _strip_html(item.get("body", ""))
    if len(body) > 500:
        body = body[:500] + "..."
    return (
        f"**{item.get('title', '')}** "
        f"(score: {item.get('score', 0)}, "
        f"answers: {item.get('answer_count', 0)}, "
        f"accepted: {item.get('is_answered', False)})\n"
        f"{body}\n"
        f"Link: {item.get('link', '')}"
    )


# pylint: disable=unused-argument
def search_stackoverflow_threads(query: str, keywords: str, logger) -> str:
    """
    Search StackOverflow for Jenkins-related threads using the
    StackExchange API.

    Args:
        query (str): The user query.
        keywords (str): Keywords extracted from the user query.
            Currently unused; reserved for future keyword-based
            filtering.
        logger: Logger object.

    Returns:
        str: Formatted results from StackOverflow, or a fallback
             message if no results are found or the API call fails.
    """
    stackoverflow_config = CONFIG.get("stackoverflow", {})
    page_size = stackoverflow_config.get("page_size", 5)
    api_key = stackoverflow_config.get("api_key")

    params = {
        "order": "desc",
        "sort": "relevance",
        "q": query,
        "tagged": "jenkins",
        "site": "stackoverflow",
        "filter": "withbody",
        "pagesize": page_size,
        "accepted": "True",
    }
    if api_key:
        params["key"] = api_key

    try:
        resp = requests.get(
            "https://api.stackexchange.com/2.3/search/advanced",
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.warning("StackOverflow API request failed: %s", exc)
        return retrieval_config["empty_context_message"]

    items = data.get("items", [])
    if not items:
        logger.info("No StackOverflow results for query: %s", query)
        return retrieval_config["empty_context_message"]

    return "\n\n---\n\n".join(_format_so_item(item) for item in items)

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
    "search_plugin_docs": search_plugin_docs,
    "search_jenkins_docs": search_jenkins_docs,
    "search_stackoverflow_threads": search_stackoverflow_threads,
    "search_community_threads": search_community_threads,
})
