"""Unit tests for the LLM answer generator.

The provider is injected, so these tests cover the fallback paths without
touching ``llm_provider`` or the provider manager's global state.
"""

import asyncio
import logging

import pytest

from api.services import answer_generator


async def collect_stream(prompt="a prompt", **kwargs):
    """Drain the streaming generator into a list of tokens."""
    return [
        token async for token in answer_generator.generate_answer_stream(
            prompt, **kwargs)
    ]


@pytest.fixture(autouse=True)
def no_current_provider(mocker):
    """Make sure no globally selected provider shadows the injected one."""
    return mocker.patch.object(
        answer_generator, "get_current_provider", return_value=None)


def test_generate_answer_returns_provider_output(mocker):
    """Test that the provider's completion is returned as-is."""
    provider = mocker.MagicMock()
    provider.generate.return_value = "the completion"

    result = answer_generator.generate_answer(
        "a prompt", fallback_provider=provider)

    assert result == "the completion"
    provider.generate.assert_called_once()


def test_generate_answer_without_provider():
    """Test the install hint when no provider is configured at all."""
    result = answer_generator.generate_answer("a prompt")

    assert result == answer_generator.PROVIDER_UNAVAILABLE_MESSAGE


def test_generate_answer_handles_runtime_error(mocker):
    """Test that a provider RuntimeError becomes a user-facing message."""
    provider = mocker.MagicMock()
    provider.generate.side_effect = RuntimeError("model exploded")

    result = answer_generator.generate_answer(
        "a prompt", fallback_provider=provider)

    assert result == answer_generator.GENERATION_FAILED_MESSAGE


def test_generate_answer_handles_unexpected_error(mocker):
    """Test that an unexpected exception is caught rather than propagated."""
    provider = mocker.MagicMock()
    provider.generate.side_effect = KeyError("boom")

    result = answer_generator.generate_answer(
        "a prompt", fallback_provider=provider)

    assert result == answer_generator.UNEXPECTED_ERROR_MESSAGE


def test_generate_answer_does_not_log_raw_prompt_at_error(mocker, caplog):
    """Test that a failing prompt is not leaked into WARNING/ERROR logs."""
    logging.getLogger("API").propagate = True
    provider = mocker.MagicMock()
    provider.generate.side_effect = RuntimeError("failed")

    with caplog.at_level(logging.ERROR):
        answer_generator.generate_answer(
            "PASSWORD=hunter2", fallback_provider=provider)

    assert "hunter2" not in caplog.text


def test_generate_answer_sanitizes_prompt_before_sending(mocker):
    """Test that secrets are redacted out of the prompt handed to the provider."""
    provider = mocker.MagicMock()
    provider.generate.return_value = "ok"

    answer_generator.generate_answer(
        "deploy with PASSWORD=hunter2", fallback_provider=provider)

    sent_prompt = provider.generate.call_args.kwargs["prompt"]
    assert "hunter2" not in sent_prompt


def test_generate_answer_stream_yields_tokens(mocker):
    """Test that streamed tokens are passed through in order."""

    async def fake_stream(prompt, max_tokens):  # pylint: disable=unused-argument
        for token in ["a", "b", "c"]:
            yield token

    provider = mocker.MagicMock()
    provider.generate_stream = fake_stream

    assert asyncio.run(collect_stream(fallback_provider=provider)) == ["a", "b", "c"]


def test_generate_answer_stream_without_provider():
    """Test that the stream yields the install hint when no provider exists."""
    assert asyncio.run(collect_stream()) == [
        answer_generator.PROVIDER_UNAVAILABLE_MESSAGE]


def test_generate_answer_stream_handles_runtime_error(mocker):
    """Test that a failure mid-stream yields the user-facing message."""

    async def failing_stream(prompt, max_tokens):  # pylint: disable=unused-argument
        # The unconditional yield below is what makes this an async generator;
        # the guard keeps it reachable so the function stays a valid generator.
        if prompt is not None:
            raise RuntimeError("stream died")
        yield ""

    provider = mocker.MagicMock()
    provider.generate_stream = failing_stream

    assert asyncio.run(collect_stream(fallback_provider=provider)) == [
        answer_generator.GENERATION_FAILED_MESSAGE]
