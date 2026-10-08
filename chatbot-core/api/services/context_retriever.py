"""Retrieval and assembly of the context handed to the answer generator.

Two retrieval paths live here:

* ``retrieve_context`` — the semantic path used by the current pipeline, which
  queries every configured source directly and optionally appends GraphRAG
  context.
* ``get_reply_simple_query_pipeline`` — the agentic path, which lets the LLM
  pick retrieval tools and scores the result for relevance before answering.

Collaborators that unit tests patch on ``chat_service`` (the document
retriever, the GraphRAG builder, the answer generator) are injected by the
caller rather than imported here, so the existing patch targets keep working
and no module ever has to import ``chat_service`` back.
"""

import re
from typing import Callable, Optional

from api.config.loader import CONFIG
from api.constants import CODE_BLOCK_PLACEHOLDER_PATTERN
from api.models.embedding_model import EMBEDDING_MODEL
from api.prompts.prompt_builder import build_prompt
from api.prompts.prompts import CONTEXT_RELEVANCE_PROMPT
from api.services.tool_dispatcher import execute_search_tools, get_agent_tool_calls
from api.tools.sanitizer import sanitize_log_payload
from api.tools.utils import make_placeholder_replacer
from utils import LoggerFactory

logger = LoggerFactory.instance().get_logger("api")
llm_config = CONFIG["llm"]
retrieval_config = CONFIG["retrieval"]

SOURCE_TOP_K_CONFIG_KEYS = {
    "plugins": "top_k_plugins",
    "docs": "top_k_docs",
    "discourse": "top_k_discourse",
}

# Signature of the answer generator injected by the caller:
# (prompt, max_tokens=None) -> str
GenerateAnswer = Callable[..., str]
# (query, embedding_model, logger=..., source_name=..., top_k=...) -> (docs, scores)
GetRelevantDocuments = Callable[..., tuple]
# (query, logger) -> str
BuildGraphContext = Optional[Callable[..., str]]


def retrieve_context(
    user_input: str,
    get_documents: GetRelevantDocuments,
    build_graph_context: BuildGraphContext = None,
) -> str:
    """
    Retrieves the most relevant document chunks for a user query across every
    configured source (plugins, jenkins docs, community threads, ...) and
    reconstructs them by replacing placeholder tokens with actual code blocks.

    Args:
        user_input (str): The input query string.
        get_documents (GetRelevantDocuments): Semantic retriever to query each source with.
        build_graph_context (BuildGraphContext): Optional GraphRAG context builder.
            ``None`` means GraphRAG is unavailable and only semantic retrieval is used.

    Returns:
        str: Combined, reconstructed context text. Returns retrieval_config["empty_context_message"]
        if any context have been retrieved.
    """
    # Dev mode: bypass RAG when indices are not built
    if CONFIG.get("dev_mode", False):
        logger.info(
            "Dev mode enabled - skipping RAG retrieval. Build indices to enable full RAG.")
        return "Dev mode: RAG indices not built. This is a placeholder context for testing."

    # Pull the same set of sources the new-architecture tools use.
    tool_names = CONFIG.get("tool_names")
    if not isinstance(tool_names, dict) or not tool_names:
        raise ValueError("tool_names missing from config")

    context_texts = []
    for source_name in tool_names.values():
        context_texts.extend(_retrieve_source_context(
            user_input, source_name, get_documents))

    if build_graph_context is None:
        logger.warning("GraphRAG is unavailable; using semantic retrieval only.")
    else:
        graph_context = build_graph_context(user_input, logger)
        if graph_context:
            context_texts.append(graph_context)

    if not context_texts:
        logger.warning(retrieval_config["empty_context_message"])
        return retrieval_config["empty_context_message"]

    return "\n\n".join(context_texts)


def _retrieve_source_context(
    user_input: str,
    source_name: str,
    get_documents: GetRelevantDocuments,
) -> list:
    """Retrieve and reconstruct the chunks of a single source."""
    top_k = retrieval_config[SOURCE_TOP_K_CONFIG_KEYS.get(
        source_name, "top_k")]
    data_retrieved, _ = get_documents(
        user_input,
        EMBEDDING_MODEL,
        logger=logger,
        source_name=source_name,
        top_k=top_k,
    )
    if not data_retrieved:
        logger.info("No relevant chunks from source '%s'.", source_name)
        return []

    context_texts = []
    for item in data_retrieved:
        item_id = item.get("id", "")
        if not item_id:
            logger.warning(
                "Id of retrieved context not found in source '%s'. Skipping element.",
                source_name,
            )
            continue
        text = item.get("chunk_text", "")
        if not text:
            logger.warning(
                "Text of chunk with ID %s (source '%s') is missing",
                item_id, source_name,
            )
            continue

        code_iter = iter(item.get("code_blocks", []))
        replace = make_placeholder_replacer(code_iter, item_id, logger)
        text = re.sub(CODE_BLOCK_PLACEHOLDER_PATTERN, replace, text)
        context_texts.append(f"[Source: {source_name}]\n{text}")

    return context_texts


def extract_relevance_score(response: str) -> int:
    """
    Extracts relevance score (0 or 1) from a response labeled with 'Label: N'; defaults to 0.
    The search is case-insensitive.

    Args:
        response (str): The LLM output containing a 'Label: N' pattern.

    Returns:
        int: 1 if the response is relevant, 0 otherwise.
    """
    match = re.search(r"Label:\s*([01])", response, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0


def get_query_context_relevance(
    query: str,
    context: str,
    generate_answer: GenerateAnswer,
) -> int:
    """
    Returns the relevance of the retrieved context to the original query.

    Args:
        query (str): The user query.
        context (str): The retrieved context.
        generate_answer (GenerateAnswer): Callable used to query the LLM.

    Returns:
        int: A relevance score (1 for relevant, 0 for not relevant).
    """
    prompt = CONTEXT_RELEVANCE_PROMPT.format(query=query, context=context)

    output = generate_answer(
        prompt, llm_config["max_tokens_query_context_relevance"])

    return extract_relevance_score(output)


def get_reply_simple_query_pipeline(
    query: str,
    memory,
    generate_answer: GenerateAnswer,
) -> str:
    """
    Executes the pipeline to answer a simple query using retrieval and generation.

    Args:
        query (str): The user query to answer.
        memory: Memory context used in prompt construction.
        generate_answer (GenerateAnswer): Callable used to query the LLM.

    Returns:
        str: The generated answer or a fallback message if relevance is too low.
    """
    iterations, relevance = -1, 0
    retrieved_context = ""
    while iterations < retrieval_config["max_reformulate_iterations"] and relevance != 1:
        tool_calls = get_agent_tool_calls(query, generate_answer)

        retrieved_context = execute_search_tools(tool_calls)

        logger.debug("Retrieved context: %s",
                     sanitize_log_payload(retrieved_context))

        relevance = get_query_context_relevance(
            query, retrieved_context, generate_answer)
        logger.info("Query context relevance %s", relevance)
        iterations += 1

    if relevance != 1:
        return f"Unfortunately we are not able to respond to your question about {query}."

    prompt = build_prompt(query, retrieved_context, memory)

    return generate_answer(prompt)
