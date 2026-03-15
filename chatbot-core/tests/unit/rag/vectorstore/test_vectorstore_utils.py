"""Unit Tests for vectorstore_utils."""
# pylint: disable=redefined-outer-name

import pickle
import pytest
from rag.vectorstore.vectorstore_utils import (
    save_faiss_index,
    load_faiss_index,
    load_metadata,
    save_metadata
)


@pytest.fixture
def mock_logger(mocker):
    """Fixture to patch LoggerFactory and return a mock logger."""
    mock_log = mocker.Mock()
    # This forces LoggerFactory to return your mock so the tests can "see" the calls
    mocker.patch(
        "utils.LoggerFactory.instance").return_value.get_logger.return_value = mock_log
    return mock_log


def test_save_faiss_index_success(mocker, tmp_path):
    """Test saving FAISS index successfully."""
    mock_index = mocker.Mock()
    mock_write_index = mocker.patch("faiss.write_index")
    local_mock_logger = mocker.Mock()
    path = tmp_path / "index.faiss"

    save_faiss_index(mock_index, str(path), local_mock_logger)

    mock_write_index.assert_called_once_with(mock_index, str(path))
    local_mock_logger.info.assert_called_once_with(
        "FAISS index saved to %s", str(path))


def test_load_faiss_index_success(mocker, tmp_path, mock_logger):
    """Test loading FAISS index successfully."""
    mock_index = mocker.Mock()
    mock_read_index = mocker.patch("faiss.read_index", return_value=mock_index)
    path = tmp_path / "index.faiss"

    result = load_faiss_index(str(path))

    mock_logger.info.assert_any_call(
        "Loading FAISS index from %s...", str(path))
    mock_logger.info.assert_any_call("FAISS index loaded successfully.")
    mock_read_index.assert_called_once_with(str(path))
    assert result == mock_index


def test_load_faiss_index_file_not_found(mocker, tmp_path, mock_logger):
    """Test that loading a non-existing index path leads to FileNotFoundError."""
    mocker.patch("faiss.read_index",
                 side_effect=FileNotFoundError("Not found details"))
    path = tmp_path / "wrong_index_path.faiss"

    result = load_faiss_index(str(path))

    mock_logger.error.assert_called_once()
    assert "File error while loading FAISS index" in mock_logger.error.call_args[0][0]
    assert result is None


def test_load_faiss_index_oserror(mocker, tmp_path, mock_logger):
    """Test OSError during the loading of the FAISS index."""
    mocker.patch("faiss.read_index", side_effect=OSError("OS error details"))
    path = tmp_path / "malformed_index.faiss"

    result = load_faiss_index(str(path))

    mock_logger.error.assert_called_once()
    assert result is None


def test_save_metadata_success(mocker, tmp_path):
    """Test that metadata is pickled successfully."""
    metadata = [{"chunk_text": "Jenkins on the moon"}]
    local_mock_logger = mocker.Mock()
    path = tmp_path / "metadata.pkl"

    save_metadata(metadata, str(path), local_mock_logger)

    assert path.exists()
    local_mock_logger.info.assert_called_once_with(
        "Metadata saved to %s", str(path))

# NOTE: Removed `mocker` from the remaining functions below


def test_load_metadata_success(tmp_path, mock_logger):
    """Test loading metadata successfully, returning the metadata."""
    data = [{"chunk_text": "Jenkins on the moon"}]
    path = tmp_path / "metadata.pkl"
    with open(path, "wb") as f:
        pickle.dump(data, f)

    result = load_metadata(str(path))

    mock_logger.info.assert_any_call("Loading metadata from %s...", str(path))
    mock_logger.info.assert_any_call("Metadata loaded successfully.")
    assert result == data


def test_load_metadata_file_not_found(tmp_path, mock_logger):
    """Testing FileNotFoundError during metadata load."""
    path = tmp_path / "no_metadata.pkl"

    result = load_metadata(str(path))

    mock_logger.error.assert_called_once()
    assert "Metadata file not found" in mock_logger.error.call_args[0][0]
    assert result is None


def test_load_metadata_deserializing_error(tmp_path, mock_logger):
    """Test unpickling error during metadata load."""
    path = tmp_path / "corrupt_metadata.pkl"
    with open(path, "wb") as f:
        f.write(b"not a pickle")

    result = load_metadata(str(path))

    mock_logger.error.assert_called_once()
    assert "Failed to load metadata" in mock_logger.error.call_args[0][0]
    assert result is None
