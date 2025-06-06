"""
Constructs the prompt used for querying the LLM, including system-level instructions,
chat history, context retrieved from the knowledge base, and the user's question.
"""

from langchain.memory import ConversationBufferMemory

SYSTEM_INSTRUCTION = """
You are JenkinsBot, an expert AI assistant specialized in Jenkins and its ecosystem.
You help users with Jenkins, CI/CD pipelines, plugin usage, configuration, and troubleshooting.

Use the provided context (retrieved from Jenkins documentation and plugin metadata) to answer questions accurately.
Also consider the prior conversation history to maintain context across turns.

If the answer is not in the context or history, reply with:
"I'm not able to answer based on the available information."

Do not hallucinate or invent facts.
"""

def build_prompt(user_query: str, context: str, memory: ConversationBufferMemory) -> str:
    """
    Build the full prompt by combining system instructions, chat history, context,and user question.

    Args:
        user_query (str): The raw question from the user.
        context (str): The relevant retrieved chunks to ground the answer.
        memory (ConversationBufferMemory): LangChain memory holding prior chat turns.

    Returns:
        str: A structured prompt for the language model.
    """
    if memory:
        history = "\n".join(
            f"{'User' if msg.type == 'human' else 'Jenkins Assistant'}: {msg.content or ''}"
            for msg in memory.chat_memory.messages
        ) if memory.chat_memory.messages  else ""
    else:
        history = ""

    prompt = f"""{SYSTEM_INSTRUCTION}
            Chat History:
            {history}

            Context:
            {context}

            User Question:
            {user_query.strip()}

            Answer:
            """

    return prompt
