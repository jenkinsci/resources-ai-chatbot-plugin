"""
Definition of the tools avaialable to the Agent.
"""

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

def analyze_jenkins_logs(query: str, logger, files: Optional[List] = None) -> str:
    """
    Log analysis tool. Extracts error signatures from provided logs
    or external sources to identify root causes of failures.

    Args:
        query (str): The search query or focus area for log analysis.
        logger: Logger for debugging.
        files (Optional[List]): Attached files that might contain logs.
    
    Returns:
        str: Extracted error details or a status message.
    """
    if not files:
        return "No local log files provided for analysis. Please upload build logs."

    # Look for files that likely contain logs
    log_contents = []
    for file in files:
        # File object is likely a FileAttachment pydantic model or dict
        filename = getattr(file, 'filename', '').lower() if hasattr(file, 'filename') else str(file.get('filename', '')).lower()
        content = getattr(file, 'content', '') if hasattr(file, 'content') else file.get('content', '')
        
        if any(ext in filename for ext in ['.log', '.txt', 'jenkins', 'build']):
            log_contents.append(f"--- File: {filename} ---\n{content[:2000]}") # Truncate for prompt safety

    if not log_contents:
        return "No relevant build logs found in the attached files."

    # We return the raw (but truncated) log segments as "Context".
    # The main LLM will use LOG_ANALYSIS_INSTRUCTION to process this.
    return "\n\n".join(log_contents)

TOOL_REGISTRY = MappingProxyType({
    "search_plugin_docs": search_plugin_docs,
    "search_jenkins_docs": search_jenkins_docs,
    "search_stackoverflow_threads": search_stackoverflow_threads,
    "search_community_threads": search_community_threads,
    "analyze_jenkins_logs": analyze_jenkins_logs,
})
