"""Fixtures for unit tests."""

import pytest
from fastapi import FastAPI
from sentence_transformers import SentenceTransformer
from api.routes.chatbot import router

@pytest.fixture
def fastapi_app() -> FastAPI:
    """Fixture to create FastAPI app instance with routes."""
    app = FastAPI()
    app.include_router(router)
    return app

@pytest.fixture
def mock_get_session(mocker):
    """Mock the memory.get_session function."""
    return mocker.patch("api.services.chat_service.get_session")

@pytest.fixture
def mock_retrieve_context(mocker):
    """Mock the retrieve_context function."""
    return mocker.patch("api.services.chat_service.retrieve_context")

@pytest.fixture
def mock_prompt_builder(mocker):
    """Mock the build_prompt function."""
    return mocker.patch("api.services.chat_service.build_prompt")

@pytest.fixture
def mock_llm_provider(mocker):
    """Mock the LLM provider generate function."""
    return mocker.patch("api.services.chat_service.llm_provider")

@pytest.fixture
def mock_get_relevant_documents(mocker):
    """Mock the get_relevant_documents function."""
    return mocker.patch("api.services.chat_service.get_relevant_documents")

@pytest.fixture
def mock_init_session(mocker):
    """Mock the init_session function."""
    return mocker.patch("api.routes.chatbot.init_session")

@pytest.fixture
def mock_session_exists(mocker):
    """Mock the session_exists function."""
    return mocker.patch("api.routes.chatbot.session_exists")

@pytest.fixture
def mock_delete_session(mocker):
    """Mock the delete_session function."""
    return mocker.patch("api.routes.chatbot.delete_session")

@pytest.fixture
def mock_get_chatbot_reply(mocker):
    """Mock the get_chatbot_reply function."""
    return mocker.patch("api.routes.chatbot.get_chatbot_reply")

@pytest.fixture
def mock_sentence_transformer(mocker):
    """Mock the SentenceTransformer class constructor."""
    return mocker.patch("rag.embedding.embedding_utils.SentenceTransformer")

@pytest.fixture
def mock_model_encode(mocker):
    """Fixture to create a mock SentenceTransformer model with encode function."""
    mock_model = mocker.create_autospec(SentenceTransformer)
    return mock_model

@pytest.fixture
def mock_collect_all_chunks(mocker):
    """Mock collect_all_chunks function."""
    return mocker.patch("rag.embedding.embed_chunks.collect_all_chunks")

@pytest.fixture
def mock_load_embedding_model(mocker):
    """Mock load_embedding_model function."""
    return mocker.patch("rag.embedding.embed_chunks.load_embedding_model")

@pytest.fixture
def mock_embed_documents(mocker):
    """Mock embed_documents function."""
    return mocker.patch("rag.embedding.embed_chunks.embed_documents")

@pytest.fixture
def patched_chunk_files(mocker):
    """Fixture to patch CHUNK_FILES."""
    return mocker.patch(
        "rag.embedding.embed_chunks.CHUNK_FILES",
        ["file1.json", "file2.json", "file3.json"]
    )

@pytest.fixture
def mock_load_chunks_from_file(mocker):
    """Mock load_chunks_from_file function."""
    return mocker.patch("rag.embedding.embed_chunks.load_chunks_from_file")

@pytest.fixture
def mock_save_faiss_index(mocker):
    """Mock save_faiss_index function."""
    return mocker.patch("rag.vectorstore.store_embeddings.save_faiss_index")

@pytest.fixture
def mock_save_metadata(mocker):
    """Mock save_metadata function."""
    return mocker.patch("rag.vectorstore.store_embeddings.save_metadata")
