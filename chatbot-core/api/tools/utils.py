"""
Utilities for the tools package.
"""

import json
import os
import re
import heapq
from types import MappingProxyType
from typing import List, Tuple, Dict, Optional
from sklearn.preprocessing import MinMaxScaler
from api.config.loader import CONFIG
from rag.retriever.retrieve import get_relevant_documents
from rag.retriever.retriever_bm25 import perform_keyword_search


retrieval_config = CONFIG["retrieval"]
CODE_BLOCK_PLACEHOLDER_PATTERN = r"\[\[(?:CODE_BLOCK|CODE_SNIPPET)_(\d+)\]\]"

TOOL_SIGNATURES = MappingProxyType({
    "search_plugin_docs": {"plugin_name": str, "query": str},
    "search_jenkins_docs": {"query": str},
    "search_stackoverflow_threads": {"query": str},
    "search_community_threads": {"query": str},
})

def get_default_tools_call(query: str):
    """
    Returns a default list of tool calls using the user query,
    covering all the retrievers tools.

    Args:
        query (str): The original query of the user.

    Returns:
        A list of tool calls that represent the default setting.
    """
    return [
        {
            "tool": "search_jenkins_docs",
            "params": {
                "query": query
            }
        },
        {
            "tool": "search_plugin_docs",
            "params": {
                "plugin_name": None,
                "query": query
            }
        },
        {
            "tool": "search_stackoverflow_threads",
            "params": {
                "query": query
            }
        },
        {
            "tool": "search_community_threads",
            "params": {
                "query": query
            }
        }
    ]

def validate_tool_calls(tool_calls_parsed: list, logger) -> bool:
    """
    Validates that each tool call has a valid tool name and matching params.

    Returns True if all tool calls are valid, False otherwise.
    """
    valid = True
    for call in tool_calls_parsed:
        tool = call.get("tool")
        params = call.get("params")

        if tool not in TOOL_SIGNATURES:
            logger.warning("Tool %s not available.", tool)
            valid = False
        else:
            expected_params = TOOL_SIGNATURES[tool]

            if not isinstance(params, dict):
                logger.warning("Params for tool %s is not a dict.", tool)
                valid = False

            for param_name, param_type in expected_params.items():
                if param_name not in params:
                    logger.warning("Tool: %s: Param %s is not expected.", tool, param_name)
                    valid = False
                if not isinstance(params[param_name], param_type):
                    logger.warning("Tool: %s: Param %s is not of the expected type %s.",
                                tool, param_name, param_type.__name__)
                    valid = False

    return valid

# pylint: disable=too-many-locals
def get_inverted_scores(
    semantic_chunk_ids: List[str],
    semantic_scores: List[float],
    keyword_chunk_ids: List[str],
    keyword_scores: List[float],
    semantic_weight: Optional[float] = 0.5,
) -> List[Tuple[float, str]]:
    """
    Combines keyword and semantic search scores into a single, normalized ranking.
    Higher original scores are better for keyword scores; lower scores are better 
    for semantic scores. Missing values are penalized by assigning them the worst 
    possible score. Scores are normalized to [0, 1], averaged with the semantic
    weight, and then inverted (multiplied by -1), making them suitable for the 
    later use as a max-heap.

    Args:
        semantic_chunk_ids (List[str]): Chunk IDs returned from semantic search.
        semantic_scores (List[float]): Corresponding semantic scores (lower is better).
        keyword_chunk_ids (List[str]): Chunk IDs returned from keyword search.
        keyword_scores (List[float]): Corresponding keyword scores (higher is better).
        semantic_weight (float): Importance weight assigned to the semantic score.

    Returns:
        List[Tuple[float, str]]: A list of (inverted_score, chunk_id)
    """
    if not 0 <= semantic_weight <= 1:
        semantic_weight = 0.5
    semantic_map = {semantic_chunk_ids[i]:semantic_scores[i]
                    for i in range(len(semantic_chunk_ids))}
    keyword_map = {keyword_chunk_ids[i]:keyword_scores[i]
                   for i in range(len(keyword_chunk_ids))}

    all_chunk_ids = set(semantic_map.keys()).union(keyword_map.keys())

    default_keyword = min(keyword_map.values()) if keyword_map else 0
    default_semantic = max(semantic_map.values()) if semantic_map else 1.5

    keyword_vals = [keyword_map.get(cid, default_keyword) for cid in all_chunk_ids]
    semantic_vals = [semantic_map.get(cid, default_semantic) for cid in all_chunk_ids]

    scaler = MinMaxScaler()
    keyword_norm = scaler.fit_transform([[v] for v in keyword_vals])
    semantic_inverted = [max(semantic_vals) - v for v in semantic_vals]
    semantic_norm = scaler.fit_transform([[v] for v in semantic_inverted])

    return [
        [float(-1 * ((1 - semantic_weight) * keyword_norm[i][0] +
                     semantic_weight * semantic_norm[i][0])), cid]
        for i, cid in enumerate(all_chunk_ids)
    ]

def extract_chunks_content(chunks: List[Dict], logger) -> str:
    """
    Builds a single context string from a list of chunks by replacing code block
    placeholders with actual code blocks.

    Args:
        chunks (List[Dict]): List of chunk dictionaries.
        logger (logging.Logger): Logger for warning messages.

    Returns:
        str: Combined chunk texts, or a fallback message if none are valid.
    """
    context_texts = []
    for item in chunks:
        item_id = item.get("id", "")
        text = item.get("chunk_text", "")
        if not item_id:
            logger.warning("Id of retrieved context not found. Skipping element.")
            continue
        if text:
            code_iter = iter(item.get("code_blocks", []))
            replace = make_placeholder_replacer(code_iter, item_id, logger)
            text = re.sub(CODE_BLOCK_PLACEHOLDER_PATTERN, replace, text)

            context_texts.append(text)
        else:
            logger.warning("Text of chunk with ID %s is missing", item_id)
    return (
        "\n\n".join(context_texts)
        if context_texts
        else retrieval_config["empty_context_message"]
    )

def is_valid_plugin(plugin_name: str) -> bool:
    """
    Checks whether the given plugin name exists in the list of known plugin names.

    Args:
        plugin_name (str): The name of the plugin to validate.

    Returns:
        bool: True if the plugin exists in the list, False otherwise.
    """
    def tokenize(item: str) -> str:
        item = item.replace('-', '')
        return item.replace(' ', '').lower()
    list_plugin_names_path = os.path.join(os.path.abspath(__file__),
                                          "..", "..", "data", "raw", "plugin_names.json")
    with open(list_plugin_names_path, "r", encoding="utf-8") as f:
        list_plugin_names = json.load(f)

    for name in list_plugin_names:
        if tokenize(plugin_name) == tokenize(name):
            return True

    return False

def filter_retrieved_data(
    semantic_data: List[Dict],
    keyword_data: List[Dict],
    plugin_name: str
) -> Tuple[List[Dict], List[Dict]]:
    """
    Filters semantic and keyword search results to only include items whose title
    matches the given plugin name.

    Args:
        semantic_data (List[Dict]): List of retrieved chunks from semantic search.
        keyword_data (List[Dict]): List of retrieved chunks from keyword search.
        plugin_name (str): The plugin name to filter against.

    Returns:
        Tuple[List[Dict], List[Dict]]: Filtered semantic and keyword data.
    """
    def tokenize(item: str) -> str:
        item = item.replace('-', '')
        return item.replace(' ', '').lower()

    semantic_filtered_data = [item for item in semantic_data
                              if tokenize(item["metadata"]["title"]) == tokenize(plugin_name)]
    keyword_filtered_data = [item for item in keyword_data
                             if tokenize(item["metadata"]["title"]) == tokenize(plugin_name)]

    return semantic_filtered_data, keyword_filtered_data

def make_placeholder_replacer(code_iter, item_id, logger):
    """
    Returns a function to replace code block placeholders in retrieved text
    with actual code snippets from the original document.

    Args:
        code_iter (iterator): Iterator over code snippets.
        item_id (str): The ID of the document chunk (used for logging).

    Returns:
        Callable[[re.Match], str]: A function to replace placeholders.
    """
    def replace(_match):
        try:
            return next(code_iter)
        except StopIteration:
            logger.warning("More placeholders than code blocks in chunk with ID %s", item_id)
            return "[MISSING_CODE]"
    return replace

def retrieve_documents(query: str, keywords: str, logger, source_name: str, embedding_model):
    """
    Retrieve documents using both semantic and keyword-based methods.

    Args:
        query (str): The user query.
        keywords (str): Keywords extracted from the user query.
        logger: Logger object.
        source_name (str): Source name to search from.
        embedding_model : The sentence transformer model used for embeddings converting.

    Returns:
        Tuple: (data_retrieved_semantic, scores_semantic, data_retrieved_keyword, scores_keyword)
    """
    data_retrieved_semantic, scores_semantic = get_relevant_documents(
        query,
        embedding_model,
        logger=logger,
        source_name=source_name,
        top_k=retrieval_config["top_k_semantic"]
    )

    keyword_results = perform_keyword_search(
        keywords,
        logger,
        source_name=source_name,
        keyword_threshold=retrieval_config["keyword_threshold"],
        top_k=retrieval_config["top_k_keyword"]
    )

    data_retrieved_keyword = [item["chunk"] for item in keyword_results]
    scores_keyword = [item["score"] for item in keyword_results]

    return data_retrieved_semantic, scores_semantic, data_retrieved_keyword, scores_keyword

# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
def extract_top_chunks(
    data_retrieved_semantic,
    scores_semantic,
    data_retrieved_keyword,
    scores_keyword,
    top_k: int,
    logger,
    semantic_weight: Optional[float] = 0.5
) -> str:
    """
    Combine semantic and keyword results, sort by scores, and extract top chunks.

    Args:
        data_retrieved_semantic: List of semantic chunks.
        scores_semantic: Corresponding semantic scores.
        data_retrieved_keyword: List of keyword chunks.
        scores_keyword: Corresponding keyword scores.
        top_k (int): Number of top results to extract.
        logger: Logger object.
        semantic_weight (float): Importance weight assigned to the semantic score.

    Returns:
        str: Extracted content from top chunks.
    """
    scores = get_inverted_scores(
        [c["id"] for c in data_retrieved_semantic], scores_semantic,
        [c["id"] for c in data_retrieved_keyword], scores_keyword,
        semantic_weight
    )

    combined_results = data_retrieved_semantic + data_retrieved_keyword
    lookup_by_id = {item["id"]: item for item in combined_results}

    heapq.heapify(scores)
    top_k_chunks = []
    i = 0
    while i < top_k and len(scores) > 0:
        item = heapq.heappop(scores)
        top_k_chunks.append(lookup_by_id.get(item[1]))
        i += 1

    return extract_chunks_content(top_k_chunks, logger)
