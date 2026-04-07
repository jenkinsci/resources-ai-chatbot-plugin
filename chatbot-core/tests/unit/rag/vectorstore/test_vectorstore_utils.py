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
    mock_logger.info.assert_called_once_with("FAISS index saved to %s", str(path))


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

    mock_logger.info.assert_any_call("Loading FAISS index from %s...", str(path))
    mock_logger.info.assert_any_call("FAISS index loaded successfully.")
    mock_read_index.assert_called_once_with(str(path))
    assert result == mock_index


def test_load_faiss_index_file_not_found(mocker, tmp_path):
    """Test that loading a non-existing index path lead to FileNotFoundError."""
    mock_logger = mocker.Mock()
    mocker.patch("faiss.read_index", side_effect=FileNotFoundError("Not found details"))
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
    """Test that metadata is pickled successfully."""
    metadata = [{"chunk_text": "Jenkins on the moon"}]
    mock_logger = mocker.Mock()
    path = tmp_path / "metadata.pkl"

    save_metadata(metadata, str(path), mock_logger)

    assert path.exists()
    mock_logger.info.assert_called_once_with("Metadata saved to %s", str(path))

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
    """Test loading metadata successfully, returning the metadata."""
    data = [{"chunk_text": "Jenkins on the moon"}]
    path = tmp_path / "metadata.pkl"
    with open(path, "wb") as f:
        pickle.dump(data, f)

    mock_logger = mocker.Mock()

    result = load_metadata(str(path), mock_logger)

    mock_logger.info.assert_any_call("Loading metadata from %s...", str(path))
    mock_logger.info.assert_any_call("Metadata loaded successfully.")
    assert result == data


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
