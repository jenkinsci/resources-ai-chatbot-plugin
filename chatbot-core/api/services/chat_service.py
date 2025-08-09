"""
Chat service layer responsible for processing the requests forwarded by the controller.
"""

import re
from typing import List, Optional
import ast
import json
from api.models.llama_cpp_provider import llm_provider
from api.config.loader import CONFIG
from api.prompts.prompt_builder import build_prompt
from api.prompts.prompts import (
    QUERY_CLASSIFIER_PROMPT,
    SPLIT_QUERY_PROMPT,
    RETRIEVER_AGENT_PROMPT,
    CONTEXT_RELEVANCE_PROMPT
)
from api.models.schemas import ChatResponse, QueryType, try_str_to_query_type
from api.services.memory import get_session
from api.models.embedding_model import EMBEDDING_MODEL
from api.tools.tools import TOOL_REGISTRY
from api.tools.utils import get_default_tools_call, validate_tool_calls, make_placeholder_replacer
from rag.retriever.retrieve import get_relevant_documents
from utils import LoggerFactory

logger = LoggerFactory.instance().get_logger("api")
llm_config = CONFIG["llm"]
retrieval_config = CONFIG["retrieval"]
CODE_BLOCK_PLACEHOLDER_PATTERN = r"\[\[(?:CODE_BLOCK|CODE_SNIPPET)_(\d+)\]\]"

def get_chatbot_reply(session_id: str, user_input: str) -> ChatResponse:
    """
    Main chatbot entry point. Retrieves context, constructs a prompt with memory,
    and generates an LLM response. Also updates the memory with the latest exchange.

    Args:
        session_id (str): The unique ID for the chat session.
        user_input (str): The latest user message.

    Returns:
        ChatResponse: The generated assistant response.
    """
    logger.info("New message from session '%s'", session_id)
    logger.info("Handling the user query: %s", user_input)

    memory = get_session(session_id)
    if memory is None:
        raise RuntimeError(f"Session '{session_id}' not found in the memory store.")

    context = retrieve_context(user_input)
    logger.info("Context retrieved: %s", context)

    prompt = build_prompt(user_input, context, memory)

    logger.info("Generating answer with prompt: %s", prompt)
    reply = generate_answer(prompt)

    memory.chat_memory.add_user_message(user_input)
    memory.chat_memory.add_ai_message(reply)

    return ChatResponse(reply=reply)


def get_chatbot_reply_new_architecture(session_id: str, user_input: str) -> ChatResponse:
    """
    Main chatbot entry point. Retrieves context, constructs a prompt with memory,
    and generates an LLM response. Also updates the memory with the latest exchange.

    Args:
        session_id (str): The unique ID for the chat session.
        user_input (str): The latest user message.

    Returns:
        ChatResponse: The generated assistant response.
    """
    logger.info("New message from session '%s'", session_id)
    logger.info("Handling the user query: %s", user_input)

    memory = get_session(session_id)
    if memory is None:
        raise RuntimeError(f"Session '{session_id}' not found in the memory store.")

    query_type = _get_query_type(user_input)

    logger.info("The provided user query is of type %s.", query_type)

    reply = _handle_query_type(user_input, query_type, memory)

    memory.chat_memory.add_user_message(user_input)
    memory.chat_memory.add_ai_message(reply)

    return ChatResponse(reply=reply)


def _get_query_type(query: str) -> QueryType:
    """
    Gets the query type that can be either 'SIMPLE', if it contains one task, or
    'MULTI' if it contains 2 or more sub-queries inside. In case the LLM produces
    a not valid output it sets by default to MULTI, since in case it of a false
    positive it won't split up the query.

    Args:
        query (str): The user query.
    
    Returns:
        QueryType: the query type, either 'SIMPLE' or 'MULTI'
    """
    prompt = QUERY_CLASSIFIER_PROMPT.format(user_query = query)
    response = generate_answer(prompt, llm_config["max_tokens_query_classifier"])
    query_type = _extract_query_type(response)

    return try_str_to_query_type(query_type, logger)


def _handle_query_type(query: str, query_type: QueryType, memory) -> str:
    """
    Handles the query generation based on the query type. If SIMPLE it will call
    the simple pipeline, otherwise it will decompose into many queries and 
    call the simple pipeline for each one.

    Args:
        query (str): The user query.
        query_type (QueryType): The query type('SIMPLE' or 'MULTI').
        memory: The conversational memory of the involved chat.
    
    Returns:
        str: The final reply of the chatbot.
    """
    if query_type == QueryType.MULTI:
        sub_queries = _get_sub_queries(query)

        answers = []
        for sub_query in sub_queries:
            logger.info("Handling the sub-query: %s.", sub_query)
            answers.append(_get_reply_simple_query_pipeline(sub_query, memory))

        reply = _assemble_response(answers)
        logger.info("Final response: %s", reply)
    else:
        reply = _get_reply_simple_query_pipeline(query, memory)

    return reply


def _get_sub_queries(query: str) -> List[str]:
    """
    Splits a complex user query into a list of single-task sub-queries.

    Args:
        query (str): The original user query.

    Returns:
        List[str]: A list of sub-queries.
    """
    prompt = SPLIT_QUERY_PROMPT.format(user_query = query)

    queries_string = generate_answer(prompt, max_tokens=len(query) * 2)

    try:
        queries = ast.literal_eval(queries_string)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
        logger.warning("Error in parsing the subqueries. The string may be not formed" \
            " correctly: %s. Setting to default array with 1 element.", queries_string)
        queries = [query]

    queries = [q.strip() for q in queries]

    return queries


def _assemble_response(answers: List[str]):
    """
    Joins multiple answers into a single formatted response.

    Args:
        answers (List[str]): A list of answer strings.

    Returns:
        str: A single string containing all answers separated by line breaks.
    """
    return "\n\n".join(answer for answer in answers)


def _get_reply_simple_query_pipeline(query: str, memory) -> str:
    """
    Executes the pipeline to answer a simple query using retrieval and generation.

    Args:
        query (str): The user query to answer.
        memory: Memory context used in prompt construction.

    Returns:
        str: The generated answer or a fallback message if relevance is too low.
    """
    iterations, relevance = -1, 0
    while iterations < retrieval_config["max_reformulate_iterations"] and relevance != 1:
        tool_calls = _get_agent_tool_calls(query)

        retrieved_context = _execute_search_tools(tool_calls)

        logger.info("Retrieved context: %s", retrieved_context)

        relevance = _get_query_context_relevance(query, retrieved_context)
        logger.info("Query context relevance %s", relevance)
        iterations += 1

    if relevance != 1:
        return f"Unfortunately we are not able to respond to your question about {query}."

    prompt = build_prompt(query, retrieved_context, memory)

    return generate_answer(prompt)


def _get_agent_tool_calls(query: str):
    """
    Uses a prompt to determine which tools should be used for information retrieval.

    Args:
        query (str): The user query.

    Returns:
        Any: A parsed representation of tool calls, validated or defaulted.
    """
    retriever_agent_prompt = RETRIEVER_AGENT_PROMPT.format(user_query = query)

    tool_calls = generate_answer(retriever_agent_prompt,
                                 llm_config["max_tokens_retriever_agent"]+ (len(query) * 3))

    logger.warning("Tool calls: %s", tool_calls)
    try:
        tool_calls_parsed = json.loads(tool_calls)
        if not validate_tool_calls(tool_calls_parsed, logger):
            logger.warning("Tool calls are not respecting the signatures." \
            "Going for the default config")
            tool_calls_parsed = get_default_tools_call(query)
    except json.JSONDecodeError:
        logger.warning("Invalid JSON syntax in the tools output: %s.", tool_calls)
        logger.warning("Calling all the search tools with default settings.")
        tool_calls_parsed = get_default_tools_call(query)
    except (KeyError, ValueError, TypeError, AttributeError) as e:
        logger.warning("JSON structure or value error(%s %s) in the tools output: %s.",
                       type(e).__name__, e, tool_calls)
        logger.warning("Calling all the search tools with default settings.")
        tool_calls_parsed = get_default_tools_call(query)

    return tool_calls_parsed


def _execute_search_tools(tool_calls) -> str:
    """
    Executes the tool calls to retrieve relevant context information.

    Args:
        tool_calls: A list of tool call specifications with tool names and parameters.

    Returns:
        str: Combined output from all retrieval tools.
    """
    retrieved_results = []
    for call in tool_calls:
        tool_name, params = call.get("tool"), call.get("params")
        tool_fn = TOOL_REGISTRY.get(tool_name)

        result = tool_fn(**params)
        retrieved_results.append({
            "tool": tool_name,
            "output": result
        })

    return "\n\n".join(
        f"[Result of the search tool {res['tool']}]:\n{res.get('output', '')}".strip()
        for res in retrieved_results
    )


def _get_query_context_relevance(query: str, context: str):
    """
    Returns the relevance of the retrieved context to the original query.

    Args:
        query (str): The user query.
        context (str): The retrieved context.

    Returns:
        str: A relevance score or label as a string.
    """
    prompt = CONTEXT_RELEVANCE_PROMPT.format(query = query, context = context)

    output = generate_answer(prompt, llm_config["max_tokens_query_context_relevance"])

    relevance_score = _extract_relevance_score(output)

    return relevance_score

# pylint: disable=duplicate-code
def retrieve_context(user_input: str) -> str:
    """
    Retrieves the most relevant document chunks for a user query
    and reconstructs them by replacing placeholder tokens with actual code blocks.

    Args:
        user_input (str): The input query string.

    Returns:
        str: Combined, reconstructed context text. Returns retrieval_config["empty_context_message"]
        if any context have been retrieved.
    """
    data_retrieved, _ = get_relevant_documents(
        user_input,
        EMBEDDING_MODEL,
        logger=logger,
        source_name="plugins",
        top_k=retrieval_config["top_k"]
    )
    if not data_retrieved:
        logger.warning(retrieval_config["empty_context_message"])
        return "No context available."

    context_texts = []
    for item in data_retrieved:
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

def generate_answer(prompt: str, max_tokens: Optional[int] = None) -> str:
    """
    Generates a completion from the language model for the given prompt.

    Args:
        prompt (str): The full prompt to send to the LLM.

    Returns:
        str: The model's generated text response.
    """
    try:
        return llm_provider.generate(prompt=prompt,
                                    max_tokens=max_tokens or llm_config["max_tokens"])
    except Exception as e: # pylint: disable=broad-exception-caught
        logger.error("LLM generation failed for prompt: %s. Error %s", prompt, e)
        return "Sorry, I'm having trouble generating a response right now."


def _extract_query_type(response: str) -> str:
    """
    Extracts 'SIMPLE' or 'MULTI' from the response if present, else returns an empty string.
    """
    match = re.search(r"\b(SIMPLE|MULTI)\b", response)
    if match:
        return match.group(1)

    return ""

def _extract_relevance_score(response: str) -> str:
    """
    Extracts relevance score (0 or 1) from a response labeled with 'Label: N'; defaults to 0.
    """
    match = re.search(r"Label:\s*([01])", response)
    if match:
        relevance_score = int(match.group(1))
    else:
        relevance_score = 0

    return relevance_score
