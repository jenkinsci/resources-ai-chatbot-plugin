"""
Definition of the tools avaialable to the Agent.
"""
import os
from typing import Optional
from types import MappingProxyType

import httpx

from api.tools.sanitizer import sanitize_logs
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


def fetch_jenkins_build_logs(job_name: str, build_number: str, logger) -> str:
    """
    Fetches and sanitizes the console logs for a specific Jenkins build.

    Args:
        job_name (str): The name of the Jenkins job.
        build_number (str): The build number (e.g., "12", "lastFailedBuild").
        logger: The logger instance.

    Returns:
        str: The sanitized log output or an error message.
    """
    # Fallback to localhost if JENKINS_URL isn't set in the environment
    jenkins_url = os.environ.get(
        "JENKINS_URL", "http://localhost:8080").rstrip("/")
    url = f"{jenkins_url}/job/{job_name}/{build_number}/consoleText"

    try:
        user = os.environ.get("JENKINS_USER")
        token = os.environ.get("JENKINS_TOKEN")
        auth = (user, token) if user and token else None

        logger.info(f"Fetching live logs from Jenkins: {url}")

        # Use httpx to grab the raw console text
        response = httpx.get(url, auth=auth, timeout=10.0)

        if response.status_code == 404:
            return (
                f"Logs not found for job '{job_name}' build #{build_number}. "
                "Verify the job name."
            )
        response.raise_for_status()

        # Pass the massive raw log through the sanitizer to save LLM tokens
        clean_logs = sanitize_logs(response.text)

        return f"Sanitized logs for {job_name} #{build_number}:\n\n{clean_logs}"

    except httpx.RequestError as e:
        logger.error(f"Jenkins connection error: {e}")
        return f"Failed to connect to Jenkins server: {e}"
    except httpx.HTTPStatusError as e:
        logger.error(f"Jenkins HTTP error: {e}")
        return f"Jenkins API rejected the request with status code: {e.response.status_code}"


TOOL_REGISTRY = MappingProxyType({
    "search_plugin_docs": search_plugin_docs,
    "search_jenkins_docs": search_jenkins_docs,
    "search_stackoverflow_threads": search_stackoverflow_threads,
    "search_community_threads": search_community_threads,
    "fetch_jenkins_build_logs": fetch_jenkins_build_logs,
})
