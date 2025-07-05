"""Unit Tests for store_embeddings module."""

import numpy as np
import faiss
import pytest
from rag.vectorstore import store_embeddings

def test_build_faiss_ivf_index_trains_and_adds_vectors(mocker):
    """Test that build_faiss_ivf_index trains and adds vectors correctly."""
    vectors = np.random.rand(10, 5).astype("float32")
    mock_logger = mocker.Mock()

    # Patch IndexFlatL2 and IndexIVFFlat to be Mocks
    mock_quantizer = mocker.Mock()
    mock_index = mocker.Mock()
    mock_index.nprobe = 0

    mock_index_cls = mocker.patch("faiss.IndexIVFFlat", return_value=mock_index)
    mock_quantizer_cls = mocker.patch("faiss.IndexFlatL2", return_value=mock_quantizer)

    result_index = store_embeddings.build_faiss_ivf_index(
        vectors,
        nlist=4,
        nprobe=2,
        logger=mock_logger
    )

    mock_quantizer_cls.assert_called_once_with(5)
    mock_index_cls.assert_called_once_with(mock_quantizer, 5, 4, faiss.METRIC_L2)
    mock_index.train.assert_called_once_with(vectors)
    mock_index.add.assert_called_once_with(vectors)
    mock_logger.info.assert_any_call("FAISS index training started...")
    mock_logger.info.assert_any_call("FAISS index training completed.")
    assert result_index.nprobe == 2


def test_build_faiss_ivf_index_raises_on_wrong_dtype(mocker):
    """Test that build_faiss_ivf_index raises Exception if vectors are not float32."""
    vectors = np.random.rand(10, 5).astype("float64")
    mock_logger = mocker.Mock()

    with pytest.raises(TypeError) as excinfo:
        store_embeddings.build_faiss_ivf_index(
            vectors,
            nlist=4,
            nprobe=2,
            logger=mock_logger
        )

    assert "Vectors must be float32" in str(excinfo.value)


def test_build_faiss_ivf_index_raises_on_1d_input(mocker):
    """Test that build_faiss_ivf_index raises Exception if vectors are 1D."""
    vectors = np.random.rand(5).astype("float32")
    mock_logger = mocker.Mock()

    with pytest.raises(ValueError) as excinfo:
        store_embeddings.build_faiss_ivf_index(
            vectors,
            nlist=4,
            nprobe=2,
            logger=mock_logger
        )

    assert "Vectors must be 2D" in str(excinfo.value)


def test_build_faiss_ivf_index_raises_on_not_np_array(mocker):
    """Test that build_faiss_ivf_index raises Exception if vectors are not numpy instance."""
    vectors = [[0.1, 0.1, 0.1],[0.3, 0.3, 0.3]]
    mock_logger = mocker.Mock()

    with pytest.raises(TypeError) as excinfo:
        store_embeddings.build_faiss_ivf_index(
            vectors,
            nlist=4,
            nprobe=2,
            logger=mock_logger
        )

    assert "Vectors must be an instance of numpy.ndarray." in str(excinfo.value)


def test_run_indexing_successful(
        mocker,
        mock_save_faiss_index,
        mock_save_metadata
    ):
    """Test that run_indexing runs the indexing pipeline correctly."""
    mock_logger = mocker.Mock()

    vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    metadata = [{"chunk_text": "chunk 1"}, {"chunk_text": "chunk 2"}]
    mock_embed_chunks = mocker.patch(
        "rag.vectorstore.store_embeddings.embed_chunks",
        return_value=(vectors, metadata)
    )
    mock_index = mocker.Mock()
    mock_build_index =  mocker.patch(
        "rag.vectorstore.store_embeddings.build_faiss_ivf_index",
        return_value=mock_index
    )

    store_embeddings.run_indexing(
        nlist=4,
        nprobe=2,
        logger=mock_logger
    )

    mock_embed_chunks.assert_called_once_with(mock_logger)
    expected_vectors_np = np.array(vectors).astype("float32")
    mock_build_index.assert_called_once()
    np.testing.assert_array_equal(
        mock_build_index.call_args[0][0],
        expected_vectors_np
    )
    assert mock_build_index.call_args[1]["nlist"] == 4
    assert mock_build_index.call_args[1]["nprobe"] == 2
    assert mock_build_index.call_args[1]["logger"] == mock_logger
    mock_save_faiss_index.assert_called_once_with(
        mock_index,
        store_embeddings.INDEX_PATH,
        mock_logger
    )
    mock_save_metadata.assert_called_once_with(
        metadata,
        store_embeddings.METADATA_PATH,
        mock_logger
    )
    assert mock_logger.info.call_count >= 1
