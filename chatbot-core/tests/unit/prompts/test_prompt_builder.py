"""Unit tests for prompt builder logic."""

from langchain.memory import ConversationBufferMemory
from api.prompts.prompt_builder import build_prompt, SYSTEM_INSTRUCTION


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


# The log_context parameter was added in PR #89 but never got test
# coverage.  These three tests cover the LOG_ANALYSIS_INSTRUCTION branch.


def test_build_prompt_with_log_context_uses_log_analysis_instruction():
    """Passing log_context should swap the system prompt to LOG_ANALYSIS_INSTRUCTION."""
    from api.prompts.prompt_builder import LOG_ANALYSIS_INSTRUCTION  # pylint: disable=import-outside-toplevel

    memory = ConversationBufferMemory(return_messages=True)
    prompt = build_prompt(
        "Why did my build fail?",
        "Jenkins pipeline docs.",
        memory,
        log_context="ERROR: Build step failed with exit code 1",
    )

    assert LOG_ANALYSIS_INSTRUCTION.strip() in prompt
    assert SYSTEM_INSTRUCTION.strip() not in prompt


def test_build_prompt_with_log_context_includes_log_data():
    """The raw log text must appear under 'User-Provided Log Data'."""
    memory = ConversationBufferMemory(return_messages=True)
    log_text = "java.lang.NullPointerException at com.example.Main"

    prompt = build_prompt("Diagnose this", "ctx", memory, log_context=log_text)

    assert "User-Provided Log Data:" in prompt
    assert log_text in prompt


def test_build_prompt_without_log_context_omits_log_section():
    """When log_context is None the prompt should use SYSTEM_INSTRUCTION
    and not contain a log-data section at all."""
    memory = ConversationBufferMemory(return_messages=True)
    prompt = build_prompt("Hello", "ctx", memory, log_context=None)

    assert SYSTEM_INSTRUCTION.strip() in prompt
    assert "User-Provided Log Data:" not in prompt
