"""
Chat service layer responsible for processing the requests forwarded by the controller.
"""

import re
from api.models.llama_cpp_provider import llm_provider
from api.config.loader import CONFIG
from api.prompts.prompt_builder import build_prompt
from api.models.schemas import ChatResponse
from api.services.memory import get_session
from api.models.embedding_model import EMBEDDING_MODEL
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
            replace = make_placeholder_replacer(code_iter, item_id)
            text = re.sub(CODE_BLOCK_PLACEHOLDER_PATTERN, replace, text)

            context_texts.append(text)
        else:
            logger.warning("Text of chunk with ID %s is missing", item_id)
    return (
        "\n\n".join(context_texts)
        if context_texts
        else retrieval_config["empty_context_message"]
    )

def generate_answer(prompt: str) -> str:
    """
    Generates a completion from the language model for the given prompt.

    Args:
        prompt (str): The full prompt to send to the LLM.

    Returns:
        str: The model's generated text response.
    """
    return llm_provider.generate(prompt=prompt, max_tokens=llm_config["max_tokens"])


def make_placeholder_replacer(code_iter, item_id):
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
