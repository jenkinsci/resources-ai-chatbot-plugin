"""Fixtures for unit tests."""

import sys
import importlib
import pytest
from fastapi import FastAPI
from sentence_transformers import SentenceTransformer
from api.routes.chatbot import router

def get_embed_chunks_module():
    """
    Helper to retrieve the actual embed_chunks MODULE object.
    This bypasses the namespace collision where 'rag.embedding.embed_chunks'
    resolves to the function instead of the module.
    """
    importlib.import_module("rag.embedding.embed_chunks")
    return sys.modules["rag.embedding.embed_chunks"]

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
def mock_process_uploaded_file(mocker):
    """Mock the process_uploaded_file function."""
    return mocker.patch("api.routes.chatbot.process_uploaded_file")

@pytest.fixture
def mock_format_file_context(mocker):
    """Mock the format_file_context function."""
    return mocker.patch("api.services.chat_service.format_file_context")

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
    mod = get_embed_chunks_module()
    return mocker.patch.object(mod, "collect_all_chunks", create=True)

@pytest.fixture
def mock_load_embedding_model(mocker):
    """Mock load_embedding_model function."""
    mod = get_embed_chunks_module()
    return mocker.patch.object(mod, "load_embedding_model")

@pytest.fixture
def mock_embed_documents(mocker):
    """Mock embed_documents function."""
    mod = get_embed_chunks_module()
    return mocker.patch.object(mod, "embed_documents")

@pytest.fixture
def patched_chunk_files(mocker):
    """Fixture to patch CHUNK_FILES."""
    mod = get_embed_chunks_module()
    return mocker.patch.object(
        mod,
        "CHUNK_FILES",
        ["file1.json", "file2.json", "file3.json"]
    )

@pytest.fixture
def mock_load_chunks_from_file(mocker):
    """Mock load_chunks_from_file function."""
    mod = get_embed_chunks_module()
    return mocker.patch.object(mod, "load_chunks_from_file")

@pytest.fixture
def mock_save_faiss_index(mocker):
    """Mock save_faiss_index function."""
    return mocker.patch("rag.vectorstore.store_embeddings.save_faiss_index")

@pytest.fixture
def mock_save_metadata(mocker):
    """Mock save_metadata function."""
    return mocker.patch("rag.vectorstore.store_embeddings.save_metadata")
