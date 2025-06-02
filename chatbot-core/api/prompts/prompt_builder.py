"""
Constructs the prompt used for querying the LLM, including system-level instructions,
context retrieved from the knowledge base, and the user's question.
"""

system_instruction = """
You are JenkinsBot, an expert AI assistant specialized in Jenkins and its ecosystem.
You help users with Jenkins, CI/CD pipelines, plugin usage, configuration, and troubleshooting.
Always answer clearly and accurately using the provided context.
If the answer is not in the context, say "I'm not able to answer based on the available information."
Do not hallucinate or make up answers.
"""

def build_prompt(user_query: str, context: str) -> str:
    """
    Build the full prompt by combining system instructions, context, and user question.

    Args:
        user_query (str): The raw question from the user.
        context (str): The relevant retrieved chunks to ground the answer.

    Returns:
        str: A structured prompt for the language model.
    """
    prompt = f"""{system_instruction}
            Context:
            {context}

            User Question:
            {user_query.strip()}

            Answer:"""

    return prompt