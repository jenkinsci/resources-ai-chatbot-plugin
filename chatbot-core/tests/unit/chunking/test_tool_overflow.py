"""Tests for the tool output truncation security wrapper."""

from api.tools.tools import truncate_tool_output, MAX_TOOL_OUTPUT_LENGTH


def test_truncate_tool_output_prevents_overflow():
    """Ensure massive tool outputs are safely truncated to prevent LLM crashes."""

    # 1. Create a dummy tool wrapped with our new security decorator
    @truncate_tool_output
    def massive_log_generator():
        return "ERROR: Stack trace line. " * 50000  # Creates a massive string

    # 2. Execute the tool
    result = massive_log_generator()

    # 3. Assert the string was successfully chopped down
    # +100 to account for our warning message
    assert len(result) <= (MAX_TOOL_OUTPUT_LENGTH + 100)

    # 4. Assert our system warning was appended
    assert "[SYSTEM WARNING: Tool output truncated" in result
