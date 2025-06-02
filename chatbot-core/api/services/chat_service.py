import re
from api.models.model import llm_provider
from api.config.loader import CONFIG
from api.prompts.prompt_builder import build_prompt
from api.models.chat import ChatResponse
from rag.retriever.retrieve import get_relevant_documents
from utils import LoggerFactory

logger = LoggerFactory.instance().get_logger("api")
llm_config = CONFIG["llm"]
retrieval_config = CONFIG["retrieval"]
CODE_BLOCK_PLACEHOLDER_PATTERN = r"\[\[(?:CODE_BLOCK|CODE_SNIPPET)_(\d+)\]\]"

def get_chatbot_reply(user_input: str) -> ChatResponse:
    logger.info("Handling the user query: %s", user_input)
    context = retrieve_context(user_input)
    logger.info("Context retrieved: %s", context)

    prompt = build_prompt(user_input, context)

    logger.info("Generating answer with prompt: %s", prompt)
    reply = generate_answer(prompt)
    return ChatResponse(reply=reply)


def retrieve_context(user_input: str) -> str:
    data_retrieved, _ = get_relevant_documents(
        user_input,
        top_k=retrieval_config["top_k"],
        logger=logger
    )
    context_texts = []
    for item in data_retrieved:
        text = item.get("chunk_text", "")
        if text:
            code_iter = iter(item["code_blocks"])
            replace = make_placeholder_replacer(code_iter, item["id"])
            text = re.sub(CODE_BLOCK_PLACEHOLDER_PATTERN, replace, text)

            context_texts.append(text)
        else:
            logger.warning("Text of chunk with ID %s is missing", item["id"])
    return "\n\n".join(context_texts)


def generate_answer(prompt: str) -> str:
    return llm_provider.generate(prompt=prompt, max_tokens=llm_config["max_tokens"])


def make_placeholder_replacer(code_iter, item_id):
    def replace(match):
        try:
            return next(code_iter)
        except StopIteration:
            logger.warning("More placeholders than code blocks in chunk with ID %s", item_id)
            return "[MISSING_CODE]"
    return replace
