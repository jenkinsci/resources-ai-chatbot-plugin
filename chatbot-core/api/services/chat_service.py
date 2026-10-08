"""Chat service layer responsible for processing the requests forwarded by the controller.

This module is pure orchestration. The individual steps live in focused
siblings and are wired together here:

* :mod:`api.services.query_classifier` — classifying and splitting queries
* :mod:`api.services.tool_dispatcher` — choosing and running retrieval tools
* :mod:`api.services.context_retriever` — retrieving and scoring context

Collaborators such as :func:`get_relevant_documents`, ``build_graph_runtime_context``
and ``llm_provider`` are imported here and passed down to those modules, so they
stay patchable on ``api.services.chat_service`` and none of the siblings ever
imports this module back.
"""

from typing import AsyncGenerator, List, Optional

from api.config.loader import CONFIG
from api.models.llama_cpp_provider import llm_provider
from api.models.provider_manager import build_provider_manager
from api.models.schemas import ChatResponse, QueryType, FileAttachment
from api.prompts.prompt_builder import build_prompt
from api.prompts.prompts import LOG_SUMMARY_PROMPT
from api.services import (
    answer_generator,
    context_retriever,
    query_classifier,
    tool_dispatcher,
)
from api.services.memory import get_session, get_session_async
from api.services.file_service import format_file_context
from api.tools.log_parser import extract_relevant_log_lines
from api.tools.sanitizer import sanitize_log_payload, sanitize_logs

try:
    from rag.graph.runtime_context import build_graph_runtime_context
except ImportError:
    build_graph_runtime_context = None

from rag.retriever.retrieve import get_relevant_documents
from utils import LoggerFactory

logger = LoggerFactory.instance().get_logger("api")
llm_config = CONFIG["llm"]
provider_manager = build_provider_manager(llm_provider)


def prepare_log_context(log_text: str) -> str:
    """
    Extract and sanitize relevant build-log lines for display and diagnosis.

    Args:
        log_text (str): Raw Jenkins build log text.

    Returns:
        str: Sanitized relevant log excerpt, or an empty string.
    """
    if not log_text or not log_text.strip():
        return ""

    relevant_log = extract_relevant_log_lines(log_text)
    sanitized_log = sanitize_logs(relevant_log)
    logger.info(
        "Prepared build log context: raw=%d chars, sanitized excerpt=%d chars",
        len(log_text),
        len(sanitized_log),
    )
    return sanitized_log


def retrieve_context(user_input: str) -> str:
    """
    Retrieves the most relevant document chunks for a user query across every
    configured source (plugins, jenkins docs, community threads, ...) and
    reconstructs them by replacing placeholder tokens with actual code blocks.

    Args:
        user_input (str): The input query string.

    Returns:
        str: Combined, reconstructed context text, or the configured empty-context
        message when nothing relevant was retrieved.
    """
    return context_retriever.retrieve_context(
        user_input,
        get_documents=get_relevant_documents,
        build_graph_context=build_graph_runtime_context,
    )


def get_chatbot_reply(
    session_id: str,
    user_input: str,
    files: Optional[List[FileAttachment]] = None
) -> ChatResponse:
    """
    Main chatbot entry point. Retrieves context, constructs a prompt with memory,
    and generates an LLM response. Also updates the memory with the latest exchange.

    Args:
        session_id (str): The unique ID for the chat session.
        user_input (str): The latest user message.
        files (Optional[List[FileAttachment]]): Optional list of file attachments.

    Returns:
        ChatResponse: The generated assistant response.
    """
    logger.info("New message from session '%s'", session_id)
    logger.debug("Handling the user query: %s",
                 sanitize_log_payload(user_input))

    memory = get_session(session_id)
    if memory is None:
        raise RuntimeError(
            f"Session '{session_id}' not found in the memory store.")

    context = retrieve_context(user_input)
    logger.debug("Context retrieved: %s", sanitize_log_payload(context))

    # Process file context if files are provided
    context = _process_file_context(context, files)

    prompt = build_prompt(user_input, context, memory)

    logger.debug("Generating answer with prompt: %s",
                 sanitize_log_payload(prompt))
    reply = generate_answer(prompt)

    # Format user message with file info for memory
    user_message = _format_user_message_for_memory(user_input, files)

    memory.chat_memory.add_user_message(user_message)
    memory.chat_memory.add_ai_message(reply)

    return ChatResponse(reply=reply)


def _process_file_context(context: str, files: Optional[List[FileAttachment]]) -> str:
    """
    Helper function to process uploaded files and append them to the context.
    """
    if not files:
        return context

    logger.info("Processing %d uploaded file(s)", len(files))
    file_dicts = [file.model_dump() for file in files]
    file_context = format_file_context(file_dicts)

    if file_context:
        logger.info("File context added: %d characters", len(file_context))
        return f"{context}\n\n[User Uploaded Files]\n{file_context}"

    return context


def _format_user_message_for_memory(user_input: str, files: Optional[List[FileAttachment]]) -> str:
    """
    Helper function to format the user message for memory storage,
    appending the names of attached files.
    """
    if not files:
        return user_input

    file_names = [f.filename for f in files]
    return f"{user_input}\n[Attached files: {', '.join(file_names)}]"


def get_chatbot_reply_new_architecture(
        session_id: str,
        user_input: str) -> ChatResponse:
    """
    Agentic chatbot entry point. Classifies the query, answers it (splitting it
    first when it carries several tasks) and updates the memory with the exchange.

    Args:
        session_id (str): The unique ID for the chat session.
        user_input (str): The latest user message.

    Returns:
        ChatResponse: The generated assistant response.
    """
    logger.info("New message from session '%s'", session_id)
    logger.debug("Handling the user query: %s",
                 sanitize_log_payload(user_input))

    memory = get_session(session_id)
    if memory is None:
        raise RuntimeError(
            f"Session '{session_id}' not found in the memory store.")

    query_type = query_classifier.get_query_type(user_input, generate_answer)

    logger.info("The provided user query is of type %s.", query_type)

    reply = _handle_query_type(user_input, query_type, memory)

    memory.chat_memory.add_user_message(user_input)
    memory.chat_memory.add_ai_message(reply)

    return ChatResponse(reply=reply)


def _handle_query_type(query: str, query_type: QueryType, memory) -> str:
    """
    Handles the query generation based on the query type. If SIMPLE it will call
    the simple pipeline, otherwise it will decompose into many queries and
    call the simple pipeline for each one.
    """
    if query_type != QueryType.MULTI:
        return context_retriever.get_reply_simple_query_pipeline(
            query, memory, generate_answer)

    sub_queries = query_classifier.get_sub_queries(query, generate_answer)

    answers = []
    for sub_query in sub_queries:
        logger.debug("Handling sub-query: %s.", sanitize_log_payload(sub_query))
        answers.append(context_retriever.get_reply_simple_query_pipeline(
            sub_query, memory, generate_answer))

    reply = query_classifier.assemble_response(answers)
    logger.debug("Final response: %s", sanitize_log_payload(reply))

    return reply


def _get_agent_tool_calls(query: str):
    """Thin wrapper kept so external callers can reach the tool dispatcher here."""
    return tool_dispatcher.get_agent_tool_calls(query, generate_answer)


def _execute_search_tools(tool_calls) -> str:
    """Thin wrapper kept so external callers can reach the tool dispatcher here."""
    return tool_dispatcher.execute_search_tools(tool_calls)


def generate_answer(prompt: str, max_tokens: Optional[int] = None) -> str:
    """
    Generates a completion from the language model for the given prompt.

    Args:
        prompt (str): The full prompt to send to the LLM.
        max_tokens (Optional[int]): Token generation limit, falling back to the config default.

    Returns:
        str: The model's generated text response.
    """
    return answer_generator.generate_answer(
        prompt, max_tokens, fallback_provider=llm_provider)


async def generate_answer_stream(
        prompt: str, max_tokens: Optional[int] = None) -> AsyncGenerator[str, None]:
    """
    Generate streaming completion from LLM.
    Args:
        prompt: Full prompt for the model
        max_tokens: Token generation limit
    Yields:
        str: Individual tokens
    """
    async for token in answer_generator.generate_answer_stream(
            prompt, max_tokens, fallback_provider=llm_provider):
        yield token


async def get_chatbot_reply_stream(
        session_id: str,
        user_input: str,
) -> AsyncGenerator[str, None]:
    """
    Streaming version of get_chatbot_reply for WebSocket clients.

    Args:
        session_id: Unique session identifier
        user_input: User's message

    Yields:
        str: Individual tokens from LLM response
    """
    logger.info("Streaming message from session '%s'", session_id)
    logger.debug("Handling user query: %s", sanitize_log_payload(user_input))

    memory = await get_session_async(session_id)

    if memory is None:
        raise RuntimeError(
            f"Session '{session_id}' not found in memory store.")

    context = retrieve_context(user_input)
    logger.debug("Context retrieved: %s", sanitize_log_payload(context))

    prompt = build_prompt(user_input, context, memory)
    logger.debug(
        "Generating streaming answer with prompt: %s",
        sanitize_log_payload(prompt)
    )

    full_reply = ""
    async for token in generate_answer_stream(prompt):
        full_reply += token
        yield token

    memory.chat_memory.add_user_message(user_input)
    memory.chat_memory.add_ai_message(full_reply)


def _generate_search_query_from_logs(log_text: str) -> str:
    """
    Uses the LLM to extract a concise error signature from the logs
    to use as a search query for the vector database.
    """
    prompt = LOG_SUMMARY_PROMPT.format(log_data=log_text)

    return generate_answer(prompt).strip()
