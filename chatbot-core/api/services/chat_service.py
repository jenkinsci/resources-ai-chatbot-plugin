from api.models.model import llm_provider
from api.config.loader import CONFIG
from api.prompts.prompt_builder import build_prompt
from api.models.chat import ChatResponse
from rag.retrieval.retrieve import get_relevant_documents
from utils import LoggerFactory

logger = LoggerFactory.instance().get_logger("api")
llm_config = CONFIG["llm"]
retrieval_config = CONFIG["retrieval"]

def get_chatbot_reply(user_input: str) -> ChatResponse:
    context = retrieve_context(user_input)
    full_prompt = f"{context}\n\n" + build_prompt(user_input)
    reply = generate_answer(full_prompt)
    return ChatResponse(reply=reply)


def retrieve_context(user_input: str) -> str:
    context_results = get_relevant_documents(
        user_input,
        top_k=retrieval_config["top_k"],
        logger=logger
    )
    context_texts = [res["metadata"].get("chunk_text", "") for res in context_results]
    return "\n\n".join(context_texts)


def generate_answer(prompt: str) -> str:
    return llm_provider.generate(prompt=prompt, max_tokens=llm_config["max_tokens"])
