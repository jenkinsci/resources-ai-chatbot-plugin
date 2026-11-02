"""Unit tests for api/tools/utils.py."""

from unittest.mock import MagicMock, patch

from api.tools.utils import (
    make_placeholder_replacer,
    filter_retrieved_data,
    get_default_tools_call,
    extract_chunks_content,
    get_inverted_scores,
    extract_top_chunks,
    retrieve_documents,
)


class TestMakePlaceholderReplacer:
    """Tests for the code block placeholder replacer factory."""

    def test_returns_code_blocks_in_order(self):
        """Test that each call returns the next code block."""
        logger = MagicMock()
        replace = make_placeholder_replacer(iter(["a", "b"]), "chunk-1", logger)

        assert replace(None) == "a"
        assert replace(None) == "b"
        logger.warning.assert_not_called()

    def test_returns_missing_code_when_exhausted(self):
        """Test that a call after the last code block returns the fallback."""
        logger = MagicMock()
        replace = make_placeholder_replacer(iter(["a", "b"]), "chunk-1", logger)
        replace(None)
        replace(None)

        assert replace(None) == "[MISSING_CODE]"

    def test_logs_warning_when_exhausted(self):
        """Test that running out of code blocks logs a warning with the item id."""
        logger = MagicMock()
        replace = make_placeholder_replacer(iter([]), "chunk-1", logger)

        replace(None)

        logger.warning.assert_called_once_with(
            "More placeholders than code blocks in chunk with ID %s", "chunk-1"
        )


class TestFilterRetrievedData:
    """Tests for filtering retrieved chunks by plugin name."""

    def test_keeps_title_with_different_formatting(self):
        """Test that case, spaces and hyphens are ignored when matching titles."""
        chunk = {"metadata": {"title": "git-plugin"}}

        semantic, keyword = filter_retrieved_data([chunk], [chunk], "Git Plugin")

        assert semantic == [chunk]
        assert keyword == [chunk]

    def test_removes_chunk_of_other_plugin(self):
        """Test that a chunk whose title does not match is removed."""
        git_plugin = {"metadata": {"title": "git-plugin"}}
        git_client = {"metadata": {"title": "git-client"}}

        semantic, keyword = filter_retrieved_data(
            [git_plugin, git_client], [git_client], "Git Plugin"
        )

        assert semantic == [git_plugin]
        assert keyword == []

    def test_match_only_in_keyword_results(self):
        """Test that a match found only by keyword search stays in the keyword list."""
        chunk = {"metadata": {"title": "git-plugin"}}

        semantic, keyword = filter_retrieved_data([], [chunk], "Git Plugin")

        assert semantic == []
        assert keyword == [chunk]

    def test_empty_inputs_return_empty_lists(self):
        """Test that empty inputs give back two empty lists."""
        semantic, keyword = filter_retrieved_data([], [], "Git Plugin")

        assert semantic == []
        assert keyword == []


class TestGetDefaultToolsCall:
    """Tests for the default list of tool calls."""

    def test_returns_all_tools(self):
        """Test that there is one call for every search tool."""
        calls = get_default_tools_call("install jenkins")

        assert [call["tool"] for call in calls] == [
            "search_jenkins_docs",
            "search_plugin_docs",
            "search_stackoverflow_threads",
            "search_community_threads",
        ]

    def test_uses_query_in_every_call(self):
        """Test that every call gets the user query."""
        calls = get_default_tools_call("install jenkins")

        for call in calls:
            assert call["params"]["query"] == "install jenkins"

    def test_plugin_name_is_none(self):
        """Test that the plugin search is not limited to one plugin."""
        calls = get_default_tools_call("install jenkins")
        plugin_call = next(call for call in calls if call["tool"] == "search_plugin_docs")

        assert plugin_call["params"]["plugin_name"] is None


class TestExtractChunksContent:
    """Tests for building the context string from chunks."""

    def test_replaces_placeholders_with_code_blocks(self):
        """Test that placeholders are replaced with the chunk's code blocks."""
        chunk = {
            "id": "chunk-1",
            "chunk_text": "Build with [[CODE_BLOCK_0]] and run [[CODE_SNIPPET_1]]",
            "code_blocks": ["mvn package", "java -jar jenkins.war"],
        }

        result = extract_chunks_content([chunk], MagicMock())

        assert result == "Build with mvn package and run java -jar jenkins.war"

    def test_joins_chunks_with_blank_line(self):
        """Test that chunk texts are separated by a blank line."""
        chunks = [
            {"id": "chunk-1", "chunk_text": "first"},
            {"id": "chunk-2", "chunk_text": "second"},
        ]

        result = extract_chunks_content(chunks, MagicMock())

        assert result == "first\n\nsecond"

    def test_skips_chunk_without_id(self):
        """Test that a chunk without an id is skipped and a warning is logged."""
        logger = MagicMock()
        chunks = [{"chunk_text": "no id"}, {"id": "chunk-2", "chunk_text": "second"}]

        result = extract_chunks_content(chunks, logger)

        assert result == "second"
        logger.warning.assert_called_once_with(
            "Id of retrieved context not found. Skipping element."
        )

    def test_skips_chunk_without_text(self):
        """Test that a chunk without text is skipped and a warning is logged."""
        logger = MagicMock()
        chunks = [{"id": "chunk-1", "chunk_text": ""}, {"id": "chunk-2", "chunk_text": "second"}]

        result = extract_chunks_content(chunks, logger)

        assert result == "second"
        logger.warning.assert_called_once_with("Text of chunk with ID %s is missing", "chunk-1")

    @patch.dict("api.tools.utils.retrieval_config", {"empty_context_message": "No context"})
    def test_returns_empty_context_message(self):
        """Test that the empty context message is returned when no chunk is valid."""
        result = extract_chunks_content([{"chunk_text": "no id"}], MagicMock())

        assert result == "No context"


class TestGetInvertedScores:
    """Tests for combining semantic and keyword scores."""

    def test_default_weight(self):
        """Test that a chunk found by both searches gets the best score."""
        result = get_inverted_scores(["a", "b", "c"], [0.25, 0.5, 0.75], ["b", "d"], [8.0, 2.0])

        scores = {chunk_id: score for score, chunk_id in result}
        assert scores == {"a": -0.5, "b": -0.75, "c": 0.0, "d": 0.0}

    def test_higher_semantic_weight(self):
        """Test that a higher semantic weight puts the best semantic match first."""
        result = get_inverted_scores(
            ["a", "b", "c"], [0.25, 0.5, 0.75], ["b", "d"], [8.0, 2.0], semantic_weight=0.75
        )

        scores = {chunk_id: score for score, chunk_id in result}
        assert scores == {"a": -0.75, "b": -0.625, "c": 0.0, "d": 0.0}

    def test_invalid_weight_falls_back_to_default(self):
        """Test that a weight outside zero to one is replaced with 0.5."""
        result = get_inverted_scores(
            ["a", "b", "c"], [0.25, 0.5, 0.75], ["b", "d"], [8.0, 2.0], semantic_weight=2
        )

        scores = {chunk_id: score for score, chunk_id in result}
        assert scores == {"a": -0.5, "b": -0.75, "c": 0.0, "d": 0.0}

    def test_only_semantic_results(self):
        """Test scores when keyword search returns nothing."""
        result = get_inverted_scores(["a", "b"], [0.25, 0.75], [], [])

        scores = {chunk_id: score for score, chunk_id in result}
        assert scores == {"a": -0.75, "b": -0.25}

    def test_no_results(self):
        """Test that no results give an empty list."""
        assert get_inverted_scores([], [], [], []) == []


class TestExtractTopChunks:
    """Tests for picking the top chunks from both searches."""

    def test_returns_top_k_chunks_in_order(self):
        """Test that only the best top_k chunks are returned, best first."""
        semantic = [
            {"id": "a", "chunk_text": "text a"},
            {"id": "b", "chunk_text": "text b"},
            {"id": "c", "chunk_text": "text c"},
        ]
        keyword = [
            {"id": "b", "chunk_text": "text b"},
            {"id": "d", "chunk_text": "text d"},
        ]

        result = extract_top_chunks(
            semantic, [0.25, 0.5, 0.75], keyword, [8.0, 2.0], top_k=2, logger=MagicMock()
        )

        assert result == "text b\n\ntext a"

    def test_semantic_weight_changes_order(self):
        """Test that a higher semantic weight changes which chunk comes first."""
        semantic = [
            {"id": "a", "chunk_text": "text a"},
            {"id": "b", "chunk_text": "text b"},
            {"id": "c", "chunk_text": "text c"},
        ]
        keyword = [
            {"id": "b", "chunk_text": "text b"},
            {"id": "d", "chunk_text": "text d"},
        ]

        result = extract_top_chunks(
            semantic, [0.25, 0.5, 0.75], keyword, [8.0, 2.0],
            top_k=2, logger=MagicMock(), semantic_weight=0.75
        )

        assert result == "text a\n\ntext b"

    def test_chunk_in_both_searches_is_not_repeated(self):
        """Test that a chunk found by both searches is returned once."""
        chunk = {"id": "b", "chunk_text": "text b"}

        result = extract_top_chunks([chunk], [0.5], [chunk], [8.0], top_k=5, logger=MagicMock())

        assert result == "text b"

    @patch.dict("api.tools.utils.retrieval_config", {"empty_context_message": "No context"})
    def test_no_results(self):
        """Test that the empty context message is returned when nothing is found."""
        result = extract_top_chunks([], [], [], [], top_k=3, logger=MagicMock())

        assert result == "No context"


class TestRetrieveDocuments:
    """Tests for retrieving documents with semantic and keyword search."""

    @patch.dict(
        "api.tools.utils.retrieval_config",
        {"top_k_semantic": 5, "keyword_threshold": 0.5, "top_k_keyword": 3},
    )
    @patch("api.tools.utils.perform_keyword_search_from_source")
    @patch("api.tools.utils.get_relevant_documents")
    def test_calls_both_searches_with_config(self, mock_semantic, mock_keyword):
        """Test that both searches get the source name and the config values."""
        mock_semantic.return_value = ([], [])
        mock_keyword.return_value = []
        logger = MagicMock()
        model = MagicMock()

        retrieve_documents("how to install jenkins", "install jenkins", logger, "docs", model)

        mock_semantic.assert_called_once_with(
            "how to install jenkins", model, logger=logger, source_name="docs", top_k=5
        )
        mock_keyword.assert_called_once_with(
            "install jenkins", logger, source_name="docs", keyword_threshold=0.5, top_k=3
        )

    @patch("api.tools.utils.perform_keyword_search_from_source")
    @patch("api.tools.utils.get_relevant_documents")
    def test_splits_keyword_results(self, mock_semantic, mock_keyword):
        """Test that keyword results are split into chunks and scores."""
        mock_semantic.return_value = ([{"id": "a"}], [0.25])
        mock_keyword.return_value = [{"chunk": {"id": "b"}, "score": 8.0}]

        result = retrieve_documents("query", "keywords", MagicMock(), "docs", MagicMock())

        assert result == ([{"id": "a"}], [0.25], [{"id": "b"}], [8.0])

    @patch("api.tools.utils.perform_keyword_search_from_source")
    @patch("api.tools.utils.get_relevant_documents")
    def test_empty_results(self, mock_semantic, mock_keyword):
        """Test that empty searches return empty lists."""
        mock_semantic.return_value = ([], [])
        mock_keyword.return_value = []

        result = retrieve_documents("query", "keywords", MagicMock(), "docs", MagicMock())

        assert result == ([], [], [], [])
