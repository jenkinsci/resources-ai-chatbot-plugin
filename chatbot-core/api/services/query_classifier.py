"""Classification and decomposition of incoming user queries.

This module decides whether a query carries a single task or several, and
splits the multi-task ones into standalone sub-queries. It never imports
``chat_service``; the LLM call is handed in as the ``generate_answer``
callable so the dependency only ever points one way.
"""

import ast
import re
from typing import Callable, List

from api.config.loader import CONFIG
from api.models.schemas import QueryType, try_str_to_query_type
from api.prompts.prompts import QUERY_CLASSIFIER_PROMPT, SPLIT_QUERY_PROMPT
from api.tools.sanitizer import sanitize_log_payload
from utils import LoggerFactory

logger = LoggerFactory.instance().get_logger("api")
llm_config = CONFIG["llm"]

# Signature of the answer generator injected by the caller:
# (prompt, max_tokens=None) -> str
GenerateAnswer = Callable[..., str]


def extract_query_type(response: str) -> str:
    """
    Extracts 'SIMPLE' or 'MULTI' from the response if present, else returns an empty string.
    The search is case-insensitive, and the result is returned in uppercase.

    Args:
        response (str): The raw LLM output of the classifier prompt.

    Returns:
        str: 'SIMPLE', 'MULTI', or an empty string when neither is present.
    """
    match = re.search(r"\b(SIMPLE|MULTI)\b", response, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    return ""


def get_query_type(query: str, generate_answer: GenerateAnswer) -> QueryType:
    """
    Gets the query type that can be either 'SIMPLE', if it contains one task, or
    'MULTI' if it contains 2 or more sub-queries inside. In case the LLM produces
    a not valid output it sets by default to MULTI, since in case it of a false
    positive it won't split up the query.

    Args:
        query (str): The user query.
        generate_answer (GenerateAnswer): Callable used to query the LLM.

    Returns:
        QueryType: the query type, either 'SIMPLE' or 'MULTI'
    """
    prompt = QUERY_CLASSIFIER_PROMPT.format(user_query=query)
    response = generate_answer(
        prompt, llm_config["max_tokens_query_classifier"])

    return try_str_to_query_type(extract_query_type(response), logger)


def get_sub_queries(query: str, generate_answer: GenerateAnswer) -> List[str]:
    """
    Splits a complex user query into a list of single-task sub-queries.

    Args:
        query (str): The original user query.
        generate_answer (GenerateAnswer): Callable used to query the LLM.

    Returns:
        List[str]: A list of sub-queries.
    """
    prompt = SPLIT_QUERY_PROMPT.format(user_query=query)

    queries_string = generate_answer(prompt, max_tokens=len(query) * 2)

    try:
        queries = ast.literal_eval(queries_string)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        logger.warning(
            "Error in parsing sub-queries. Falling back to single query mode.")
        logger.debug("Failed sub-query payload: %s",
                     sanitize_log_payload(queries_string))
        queries = [query]

    return [q.strip() for q in queries]


def assemble_response(answers: List[str]) -> str:
    """
    Joins multiple answers into a single formatted response.

    Args:
        answers (List[str]): A list of answer strings.

    Returns:
        str: A single string containing all answers separated by line breaks.
    """
    return "\n\n".join(answer for answer in answers)
