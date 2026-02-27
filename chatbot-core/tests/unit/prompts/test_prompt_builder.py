"""Unit tests for prompt builder logic."""

from langchain.memory import ConversationBufferMemory
from api.prompts.prompt_builder import build_prompt, SYSTEM_INSTRUCTION
from api.prompts.prompts import LOG_ANALYSIS_INSTRUCTION


def test_build_prompt_with_full_history_and_context():
    """Test prompt formatting with user + assistant chat history and context."""
    memory = ConversationBufferMemory(return_messages=True)
    memory.chat_memory.add_user_message("How do I configure a Jenkins job?") # pylint: disable=no-member
    memory.chat_memory.add_ai_message("You can use the freestyl option.") # pylint: disable=no-member
    context = "You can configure Jenkins jobs using freestyle option or pipelines."
    user_query = "What about using pipelines?"

    prompt = build_prompt(user_query, context, memory)

    chat_idx, context_idx, question_idx, answer_idx = get_prompt_indexes(prompt)
    history_section, context_section, question_section = get_prompt_sections(prompt)

    assert SYSTEM_INSTRUCTION.strip() in prompt
    assert chat_idx < context_idx < question_idx < answer_idx
    assert "User: How do I configure a Jenkins job?" in history_section
    assert "Jenkins Assistant: You can use the freestyl option." in history_section
    assert context in context_section
    assert user_query.strip() in question_section
    assert prompt.strip().endswith("Answer:")


def test_build_prompt_with_empty_history():
    """Test prompt formatting when no prior messages exist."""
    memory = ConversationBufferMemory(return_messages=True)
    context = "Relevant Jenkins documentation here."
    user_query = "How do I install plugins?"

    prompt = build_prompt(user_query, context, memory)

    chat_idx, context_idx, question_idx, answer_idx = get_prompt_indexes(prompt)
    history_section, context_section, question_section = get_prompt_sections(prompt)

    assert SYSTEM_INSTRUCTION.strip() in prompt
    assert chat_idx < context_idx < question_idx < answer_idx
    assert history_section.strip() == ""
    assert user_query in question_section
    assert context in context_section


def test_build_prompt_with_no_context_and_whitespace_query():
    """Test prompt formatting when context is missing and question has extra spaces."""
    memory = ConversationBufferMemory(return_messages=True)
    user_query = "   How can I trigger a build manually?   "
    context = ""

    prompt = build_prompt(user_query, context, memory)

    chat_idx, context_idx, question_idx, answer_idx = get_prompt_indexes(prompt)
    _, context_section, question_section = get_prompt_sections(prompt)

    assert SYSTEM_INSTRUCTION.strip() in prompt
    assert chat_idx < context_idx < question_idx < answer_idx
    assert context_section.strip() == ""
    assert user_query.strip() in question_section

def test_build_prompt_with_none_memory():
    """Test that prompt works if memory is None (no chat history)."""
    context = "Some Jenkins context."
    user_query = "What is a build trigger?"

    prompt = build_prompt(user_query, context, memory=None)

    chat_idx, context_idx, question_idx, answer_idx = get_prompt_indexes(prompt)
    history_section, context_section, question_section = get_prompt_sections(prompt)

    assert SYSTEM_INSTRUCTION.strip() in prompt
    assert chat_idx < context_idx < question_idx < answer_idx
    assert history_section.strip() == ""
    assert context in context_section
    assert user_query in question_section

def test_build_prompt_with_log_context_uses_log_analysis_instruction():
    """Test that providing log_context switches to LOG_ANALYSIS_INSTRUCTION
    and includes the 'User-Provided Log Data' section in the prompt."""
    memory = ConversationBufferMemory(return_messages=True)
    context = "Jenkins pipeline documentation."
    user_query = "Why did my build fail?"
    log_context = "ERROR: Build step 'Execute shell' marked build as failure"

    prompt = build_prompt(user_query, context, memory, log_context=log_context)

    # Should use LOG_ANALYSIS_INSTRUCTION, NOT SYSTEM_INSTRUCTION
    assert LOG_ANALYSIS_INSTRUCTION.strip() in prompt
    assert SYSTEM_INSTRUCTION.strip() not in prompt

    # Log section must be present with the actual log data
    assert "User-Provided Log Data:" in prompt
    assert log_context in prompt

    # Standard structural sections still present and in order
    chat_idx, context_idx, question_idx, answer_idx = get_prompt_indexes(prompt)
    assert chat_idx < context_idx < question_idx < answer_idx

    # User query still appears correctly
    _, _, question_section = get_prompt_sections(prompt)
    assert user_query.strip() in question_section


def test_build_prompt_with_log_context_and_history():
    """Test the full combination: log_context + conversation history + context."""
    memory = ConversationBufferMemory(return_messages=True)
    memory.chat_memory.add_user_message("My build failed.") # pylint: disable=no-member
    memory.chat_memory.add_ai_message("Can you share the logs?") # pylint: disable=no-member
    context = "Check Jenkins console output for errors."
    user_query = "Here are my logs, can you analyze?"
    log_context = "java.lang.OutOfMemoryError: Java heap space"

    prompt = build_prompt(user_query, context, memory, log_context=log_context)

    # Uses log analysis instruction
    assert LOG_ANALYSIS_INSTRUCTION.strip() in prompt
    assert SYSTEM_INSTRUCTION.strip() not in prompt

    # History is preserved
    history_section, context_section, question_section = get_prompt_sections(prompt)
    assert "User: My build failed." in history_section
    assert "Jenkins Assistant: Can you share the logs?" in history_section

    # Context and log data are both present
    assert context in context_section
    assert "User-Provided Log Data:" in prompt
    assert log_context in prompt

    # Question appears correctly
    assert user_query.strip() in question_section


def test_build_prompt_with_empty_string_log_context_uses_system_instruction():
    """Test that an empty string log_context (falsy) does NOT trigger the
    log analysis branch — should fall back to SYSTEM_INSTRUCTION."""
    memory = ConversationBufferMemory(return_messages=True)
    context = "Some context."
    user_query = "How do I configure agents?"

    prompt = build_prompt(user_query, context, memory, log_context="")

    # Should use standard instruction since "" is falsy
    assert SYSTEM_INSTRUCTION.strip() in prompt
    assert LOG_ANALYSIS_INSTRUCTION.strip() not in prompt
    assert "User-Provided Log Data:" not in prompt


def test_build_prompt_with_none_log_context_uses_system_instruction():
    """Test that log_context=None (the default) does NOT trigger the
    log analysis branch."""
    memory = ConversationBufferMemory(return_messages=True)
    context = "Some context."
    user_query = "How do I set up a pipeline?"

    prompt = build_prompt(user_query, context, memory, log_context=None)

    assert SYSTEM_INSTRUCTION.strip() in prompt
    assert LOG_ANALYSIS_INSTRUCTION.strip() not in prompt
    assert "User-Provided Log Data:" not in prompt

def test_build_prompt_with_multiple_conversation_turns():
    """Test that multiple rounds of user/assistant messages are all
    captured in the Chat History section in the correct order."""
    memory = ConversationBufferMemory(return_messages=True)
    memory.chat_memory.add_user_message("What is a Jenkinsfile?") # pylint: disable=no-member
    memory.chat_memory.add_ai_message("A Jenkinsfile defines your pipeline.") # pylint: disable=no-member
    memory.chat_memory.add_user_message("Can I use it with GitHub?") # pylint: disable=no-member
    memory.chat_memory.add_ai_message("Yes, you can integrate it with GitHub.") # pylint: disable=no-member
    context = "Jenkinsfile supports declarative and scripted syntax."
    user_query = "Show me an example."

    prompt = build_prompt(user_query, context, memory)

    history_section, _, _ = get_prompt_sections(prompt)

    # All four messages must appear in history
    assert "User: What is a Jenkinsfile?" in history_section
    assert "Jenkins Assistant: A Jenkinsfile defines your pipeline." in history_section
    assert "User: Can I use it with GitHub?" in history_section
    assert "Jenkins Assistant: Yes, you can integrate it with GitHub." in history_section

    # Order: first user message appears before second user message
    first_user_pos = history_section.index("User: What is a Jenkinsfile?")
    second_user_pos = history_section.index("User: Can I use it with GitHub?")
    assert first_user_pos < second_user_pos


def test_build_prompt_with_none_content_message():
    """Test that a message with None content is handled gracefully
    (the `msg.content or ''` guard in the source)."""
    memory = ConversationBufferMemory(return_messages=True)
    memory.chat_memory.add_user_message("Hello") # pylint: disable=no-member
    # Simulate a None content message by directly manipulating memory
    memory.chat_memory.messages[-1].content = None  # pylint: disable=no-member
    context = "Jenkins docs."
    user_query = "Test query"

    prompt = build_prompt(user_query, context, memory)

    history_section, _, _ = get_prompt_sections(prompt)
    # Should show "User: " with empty content, not crash
    assert "User: " in history_section


def test_build_prompt_with_special_characters_in_query():
    """Test that special characters (unicode, newlines) in the user query
    are preserved correctly in the output prompt."""
    memory = ConversationBufferMemory(return_messages=True)
    context = "Jenkins configuration docs."
    user_query = "  How do I use the 'pipeline' with \"quotes\" & <angle> brackets?\n  "

    prompt = build_prompt(user_query, context, memory)

    _, _, question_section = get_prompt_sections(prompt)
    assert user_query.strip() in question_section


def test_build_prompt_log_data_section_appears_between_context_and_question():
    """Test that the 'User-Provided Log Data' section is placed
    after the context section and before the user question."""
    memory = ConversationBufferMemory(return_messages=True)
    context = "Pipeline troubleshooting guide."
    user_query = "Analyze this error."
    log_context = "FATAL: command execution failed"

    prompt = build_prompt(user_query, context, memory, log_context=log_context)

    context_idx = prompt.index("Context (Documentation & Knowledge Base):")
    log_data_idx = prompt.index("User-Provided Log Data:")
    question_idx = prompt.index("User Question:")

    # Log data must appear AFTER context and BEFORE question
    assert context_idx < log_data_idx < question_idx

def get_prompt_indexes(prompt: str) -> tuple[int, int, int, int]:
    """Helper to extract section positions in the prompt."""
    chat_idx = prompt.index("Chat History:")
    context_idx = prompt.index("Context (Documentation & Knowledge Base):")
    question_idx = prompt.index("User Question:")
    answer_idx = prompt.index("Answer:")

    return chat_idx, context_idx, question_idx, answer_idx

def get_prompt_sections(prompt: str) -> tuple[str, str, str]:
    """Helper to extract prompt sections by label."""
    history_part = prompt.split("Chat History:")[1]
    history_section = history_part.split("Context (Documentation & Knowledge Base):")[0]

    context_part = prompt.split("Context (Documentation & Knowledge Base):")[1]
    context_section = context_part.split("User Question:")[0]

    question_section = prompt.split("User Question:")[1].split("Answer:")[0]

    return history_section, context_section, question_section
