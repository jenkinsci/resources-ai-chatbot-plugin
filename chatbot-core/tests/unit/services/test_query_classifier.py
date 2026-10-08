"""Unit tests for the query classifier.

Every test here drives the module with a plain stub for ``generate_answer``.
No fixture patches ``api.services.chat_service``, which is the point of the
extraction: classification can be exercised without standing up the LLM
provider, the retriever or the session memory.
"""

import logging

import pytest

from api.models.schemas import QueryType
from api.services import query_classifier


def stub_generator(*responses):
    """Build a generate_answer stub that returns the given responses in order."""
    queue = list(responses)

    def _generate(_prompt, max_tokens=None):  # pylint: disable=unused-argument
        return queue.pop(0)

    return _generate


@pytest.mark.parametrize(
    "response,expected",
    [
        ("SIMPLE", "SIMPLE"),
        ("multi", "MULTI"),
        ("The query is Simple.", "SIMPLE"),
        ("neither label here", ""),
        ("", ""),
    ],
)
def test_extract_query_type(response, expected):
    """Test that the label is pulled out case-insensitively, or left empty."""
    assert query_classifier.extract_query_type(response) == expected


def test_get_query_type_simple():
    """Test that a SIMPLE label maps to QueryType.SIMPLE."""
    result = query_classifier.get_query_type(
        "How do I install a plugin?", stub_generator("SIMPLE"))

    assert result == QueryType.SIMPLE


def test_get_query_type_multi():
    """Test that a MULTI label maps to QueryType.MULTI."""
    result = query_classifier.get_query_type(
        "Install a plugin and configure a job", stub_generator("MULTI"))

    assert result == QueryType.MULTI


def test_get_query_type_unparsable_defaults_to_multi():
    """Test that an unusable classifier output falls back to MULTI.

    MULTI is the safe default: a false positive only splits a query that did
    not need splitting, whereas a false SIMPLE drops half the user's request.
    """
    result = query_classifier.get_query_type(
        "Some query", stub_generator("I am not a label"))

    assert result == QueryType.MULTI


def test_get_sub_queries_parses_list():
    """Test that a well-formed list literal is parsed and stripped."""
    generate = stub_generator("['  install a plugin ', 'configure a job']")

    result = query_classifier.get_sub_queries("Do both things", generate)

    assert result == ["install a plugin", "configure a job"]


def test_get_sub_queries_falls_back_on_malformed_output(caplog):
    """Test that unparsable output falls back to the original single query."""
    logging.getLogger("API").propagate = True
    generate = stub_generator("not a python list at all")

    with caplog.at_level(logging.WARNING):
        result = query_classifier.get_sub_queries("Original query", generate)

    assert result == ["Original query"]
    assert "Falling back to single query mode" in caplog.text


def test_get_sub_queries_does_not_log_raw_payload_at_warning(caplog):
    """Test that the unparsable payload itself is not leaked at WARNING level."""
    logging.getLogger("API").propagate = True
    secret_payload = "API_KEY=super-secret-value"
    generate = stub_generator(secret_payload)

    with caplog.at_level(logging.WARNING):
        query_classifier.get_sub_queries("Original query", generate)

    assert "super-secret-value" not in caplog.text


def test_assemble_response_joins_with_blank_line():
    """Test that answers are joined into one response separated by blank lines."""
    assert query_classifier.assemble_response(
        ["first", "second"]) == "first\n\nsecond"


def test_assemble_response_empty():
    """Test that assembling no answers yields an empty string."""
    assert query_classifier.assemble_response([]) == ""
