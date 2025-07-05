"""Unit Tests for embed_chunks module."""

import json
from rag.embedding.embed_chunks import embed_chunks, collect_all_chunks, load_chunks_from_file

def test_embed_chunks_valid_chunks(
    mock_collect_all_chunks,
    mock_load_embedding_model,
    mock_embed_documents,
    mocker
):
    """Testing that embed_chunks processes valid chunks correctly."""
    mock_collect_all_chunks.return_value = get_mock_chunks("valid")
    mock_model = mocker.Mock()
    mock_load_embedding_model.return_value = mock_model
    mock_embed_documents.return_value = ["vec1", "vec2"]

    mock_logger = mocker.Mock()

    vectors, metadata = embed_chunks(mock_logger)

    assert vectors == ["vec1", "vec2"]
    assert len(metadata) == 2
    assert metadata[0]["id"] == "1"
    assert metadata[1]["code_blocks"] == ["some code"]

    mock_load_embedding_model.assert_called_once()
    mock_embed_documents.assert_called_once_with(
        ["Chunk text 1", "Chunk text 2"],
        mock_model,
        mock_logger
    )


def test_embed_chunks_skips_invalid_chunks(
    mock_collect_all_chunks,
    mock_load_embedding_model,
    mock_embed_documents,
    mocker
):
    """Testing that embed_chunks skips invalid chunks and logs warnings."""
    mock_collect_all_chunks.return_value = get_mock_chunks("invalid")
    mock_model = mocker.Mock()
    mock_load_embedding_model.return_value = mock_model
    mock_embed_documents.return_value = ["vec3"]

    mock_logger = mocker.Mock()

    vectors, metadata = embed_chunks(mock_logger)

    assert vectors == ["vec3"]
    assert len(metadata) == 1
    assert metadata[0]["id"] == "3"

    mock_embed_documents.assert_called_once_with(
        ["Good text"],
        mock_model,
        mock_logger
    )


def test_collect_all_chunks_with_custom_files(
    patched_chunk_files,
    mock_load_chunks_from_file,
    mocker
):
    """Testing that collect_all_chunks aggregates chunks and logs warnings for empty files."""
    _ = patched_chunk_files
    mock_load_chunks_from_file.side_effect = [
        get_mock_chunks("valid"),
        get_mock_chunks("invalid"),
        []
    ]

    mock_logger = mocker.Mock()

    chunks = collect_all_chunks(mock_logger)

    assert len(chunks) == (len(get_mock_chunks("valid")) + len(get_mock_chunks("invalid")))
    assert mock_load_chunks_from_file.call_count == 3
    mock_logger.warning.assert_called_once_with(
        "No chunks available from %s.", "file3.json"
    )


def test_load_chunks_from_file_success(mocker):
    """Test loading JSON content successfully."""
    mock_logger = mocker.Mock()

    json_data = get_mock_chunks("valid")
    mock_open = mocker.mock_open(read_data=json.dumps(json_data))
    mocker.patch("builtins.open", mock_open)

    result = load_chunks_from_file("chunks_path.json", mock_logger)

    assert result == json_data
    mock_logger.error.assert_not_called()


def test_load_chunks_from_file_file_error(mocker):
    """Test handling FileNotFoundError."""
    mock_logger = mocker.Mock()

    mocker.patch("builtins.open", side_effect=FileNotFoundError("no file"))

    result = load_chunks_from_file("missing_file.json", mock_logger)

    assert result == []
    mock_logger.error.assert_called_once()
    assert "File error while reading" in mock_logger.error.call_args[0][0]


def test_load_chunks_from_file_json_decode_error(mocker):
    """Test handling JSONDecodeError."""
    mock_logger = mocker.Mock()

    mock_open = mocker.mock_open(read_data="data in not json format")
    mocker.patch("builtins.open", mock_open)
    mocker.patch("json.load", side_effect=json.JSONDecodeError("Expecting value", "doc", 0))

    result = load_chunks_from_file("invalid.json", mock_logger)

    assert result == []
    mock_logger.error.assert_called_once()
    assert "JSON decode error" in mock_logger.error.call_args[0][0]


def test_embed_chunks_with_all_invalid_chunks(
    mock_collect_all_chunks,
    mock_load_embedding_model,
    mock_embed_documents,
    mocker
):
    """Test embed_chunks returns empty lists if all chunks are invalid."""
    mock_collect_all_chunks.return_value = get_mock_chunks("all-invalid")

    mock_logger = mocker.Mock()

    _, _ = embed_chunks(mock_logger)

    mock_embed_documents.assert_called_once_with(
        [],
        mock_load_embedding_model.return_value,
        mock_logger
    )
    assert mock_logger.warning.call_count >= 1


def test_embed_chunks_with_no_chunks(
    mock_collect_all_chunks,
    mock_load_embedding_model,
    mock_embed_documents,
    mocker
):
    """Test embed_chunks returns empty lists if no chunks are loaded."""
    mock_collect_all_chunks.return_value = []

    mock_logger = mocker.Mock()

    _, _ = embed_chunks(mock_logger)

    mock_embed_documents.assert_called_once_with(
        [],
        mock_load_embedding_model.return_value,
        mock_logger
    )
    mock_logger.info.assert_any_call("Collected %d chunks.", 0)


def get_mock_chunks(chunk_type: str):
    """Helper to get mock chunks for embedding tests."""
    if chunk_type == "valid":
        return [
            {
                "id": "1",
                "chunk_text": "Chunk text 1",
                "metadata": {"source": "doc1"},
                "code_blocks": []
            },
            {
                "id": "2",
                "chunk_text": "Chunk text 2",
                "metadata": {"source": "doc2"},
                "code_blocks": ["some code"]
            }
        ]
    if chunk_type == "invalid":
        return [
            {
                "id": "1",
                "chunk_text": "",
                "metadata": {"source": "doc1"},
            },
            {
                "id": "2",
                "chunk_text": "Valid text",
                "metadata": None,
            },
            {
                "id": "3",
                "chunk_text": "Good text",
                "metadata": {"source": "doc3"},
                "code_blocks": []
            }
        ]
    if chunk_type == "all-invalid":
        return [
            {"id": "1", "chunk_text": "", "metadata": None},
            {"id": "2", "chunk_text": "", "metadata": {}}
        ]
    return []
