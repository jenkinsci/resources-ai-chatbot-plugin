"""Unit Tests for vectorstore_utils."""

import pickle
from rag.vectorstore.vectorstore_utils import (
    save_faiss_index,
    load_faiss_index,
    load_metadata,
    save_metadata
)


def test_save_faiss_index_success(mocker, tmp_path):
    """Test saving FAISS index successfully."""
    mock_index = mocker.Mock()
    mock_write_index = mocker.patch("faiss.write_index")
    mock_logger = mocker.Mock()
    path = tmp_path / "index.faiss"

    save_faiss_index(mock_index, str(path), mock_logger)

    mock_write_index.assert_called_once_with(mock_index, str(path))
    mock_logger.info.assert_called_once_with(
        "FAISS index saved to %s", str(path))


def test_save_faiss_index_on_oserror(mocker, tmp_path):
    """Test OSError during save of FAISS index."""
    mock_index = mocker.Mock()
    mock_logger = mocker.Mock()
    mocker.patch("faiss.write_index", side_effect=OSError("Os error details"))
    path = tmp_path / "index.faiss"

    save_faiss_index(mock_index, str(path), mock_logger)

    mock_logger.error.assert_called_once()
    assert "Failed to save FAISS index" in mock_logger.error.call_args[0][0]


def test_load_faiss_index_success(mocker, tmp_path):
    """Test loading FAISS index successfully."""
    mock_index = mocker.Mock()
    mock_read_index = mocker.patch("faiss.read_index", return_value=mock_index)
    mock_logger = mocker.Mock()
    path = tmp_path / "index.faiss"

    result = load_faiss_index(str(path), mock_logger)

    mock_logger.info.assert_any_call(
        "Loading FAISS index from %s...", str(path))
    mock_logger.info.assert_any_call("FAISS index loaded successfully.")
    mock_read_index.assert_called_once_with(str(path))
    assert result == mock_index


def test_load_faiss_index_file_not_found(mocker, tmp_path):
    """Test that loading a non-existing index path lead to FileNotFoundError."""
    mock_logger = mocker.Mock()
    mocker.patch("faiss.read_index",
                 side_effect=FileNotFoundError("Not found details"))
    path = tmp_path / "wrong_index_path.faiss"

    result = load_faiss_index(str(path), mock_logger)

    mock_logger.error.assert_called_once()
    assert "File error while loading FAISS index" in mock_logger.error.call_args[0][0]
    assert result is None


def test_load_faiss_index_oserror(mocker, tmp_path):
    """Test OSError during the loading of the FAISS index."""
    mock_logger = mocker.Mock()
    mocker.patch("faiss.read_index", side_effect=OSError("OS error details"))
    path = tmp_path / "malformed_index.faiss"

    result = load_faiss_index(str(path), mock_logger)

    mock_logger.error.assert_called_once()
    assert result is None


def test_save_metadata_success(mocker, tmp_path):
    """Test that metadata is securely saved as JSON, even if .pkl is passed."""
    from rag.vectorstore.vectorstore_utils import save_metadata

    metadata = [{"chunk_text": "Jenkins on the moon"}]
    mock_logger = mocker.Mock()

    # Pass a legacy .pkl path to ensure the function intercepts and secures it
    pkl_path = tmp_path / "metadata.pkl"
    json_path = tmp_path / "metadata.json"

    save_metadata(metadata, str(pkl_path), mock_logger)

    # Assert the JSON file was created and the PKL was not
    assert json_path.exists()
    assert not pkl_path.exists()
    mock_logger.info.assert_called_with(
        "Metadata securely saved to %s", str(json_path))


def test_save_metadata_logs_error_on_exception(mocker, tmp_path):
    """Test that error during pickle dumping."""
    metadata = [{"chunk_text": "bad_text"}]
    mock_logger = mocker.Mock()
    mocker.patch("builtins.open", side_effect=OSError("permission denied"))
    path = tmp_path / "metadata.pkl"

    save_metadata(metadata, str(path), mock_logger)

    mock_logger.error.assert_called_once()
    assert "Failed to save metadata" in mock_logger.error.call_args[0][0]


def test_load_metadata_success(mocker, tmp_path):
    """Test loading legacy metadata successfully triggers the security warning."""
    import pickle
    from rag.vectorstore.vectorstore_utils import load_metadata

    data = [{"chunk_text": "Jenkins on the moon"}]
    path = tmp_path / "metadata.pkl"
    with open(path, "wb") as f:
        pickle.dump(data, f)

    mock_logger = mocker.Mock()

    result = load_metadata(str(path), mock_logger)

    # Assert the data loaded correctly
    assert result == data

    # Assert the security fallback warning was triggered
    mock_logger.warning.assert_called_once()
    assert "SECURITY WARNING: Loading legacy pickle metadata" in mock_logger.warning.call_args[
        0][0]


def test_load_metadata_file_not_found(mocker, tmp_path):
    """Testing FileNotFoundError during metadata load."""
    mock_logger = mocker.Mock()
    path = tmp_path / "no_metadata.pkl"

    result = load_metadata(str(path), mock_logger)

    mock_logger.error.assert_called_once()
    assert "Metadata file not found" in mock_logger.error.call_args[0][0]
    assert result is None


def test_load_metadata_deserializing_error(mocker, tmp_path):
    """Test unpickling error during metadata load."""
    path = tmp_path / "corrupt_metadata.pkl"
    with open(path, "wb") as f:
        f.write(b"not a pickle")
    mock_logger = mocker.Mock()

    result = load_metadata(str(path), mock_logger)

    mock_logger.error.assert_called_once()
    assert "Failed to load metadata" in mock_logger.error.call_args[0][0]
    assert result is None
