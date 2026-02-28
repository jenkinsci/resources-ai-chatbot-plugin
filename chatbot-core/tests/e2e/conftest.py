"""
E2E test configuration.

Fixtures here set up an isolated environment for each test:

- ``session_data_dir``  — redirects session file I/O to a per-test ``tmp_path``
- ``stub_llm``          — injects ``StubLLMProvider`` so the full call chain
                          runs without loading a 4 GB model
- ``e2e_client``        — a ``TestClient`` wired to the real FastAPI app with
                          all patches applied

Design notes
------------
* The embedding model (``SentenceTransformer``) is loaded at import time
  deep in the ``api.routes.chatbot`` import chain.  We short-circuit this
  by pre-populating ``sys.modules`` with a fake ``sentence_transformers``
  module *before* any application code is imported.  This avoids the
  300 MB+ download and multi-second model load.
* ``scope="function"`` everywhere: each test gets a fully isolated ``tmp_path``
  and a fresh ``StubLLMProvider`` instance.
* ``dev_mode`` is enabled in the config so RAG retrieval is bypassed.
  Part 2 (#194) will add scenarios that exercise the real FAISS path via
  ``seed_faiss.py``.
* We use ``TestClient`` as a context manager so that Starlette flushes
  ``BackgroundTasks`` (like ``persist_session``) on ``__exit__``.  This
  avoids ``time.sleep`` hacks.
"""

import shutil
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Pre-populate sys.modules with stubs for heavy optional dependencies.
#
# The import chain  api.routes.chatbot → api.services.chat_service →
# api.models.embedding_model → rag.embedding.embedding_utils →
# sentence_transformers  triggers a SentenceTransformer model download
# at import time.  We inject a fake module so the import succeeds
# instantly and ``load_embedding_model`` returns a lightweight mock.
#
# Similarly, ``rag.vectorstore.vectorstore_utils`` imports ``faiss`` and
# ``api.routes.chatbot`` tries to import ``retriv`` / ``llama_cpp``.
# We stub these if they aren't already installed.
# ---------------------------------------------------------------------------

def _make_stub_module(name: str) -> types.ModuleType:
    """Create a stub module that returns ``MagicMock`` for any attribute."""
    mod = types.ModuleType(name)
    mod.__file__ = f"<e2e-stub {name}>"
    mod.__loader__ = None
    mod.__spec__ = None

    def _getattr(attr: str):
        if attr.startswith("__") and attr.endswith("__"):
            raise AttributeError(attr)
        return MagicMock(name=f"{name}.{attr}")

    mod.__getattr__ = _getattr
    return mod


import importlib.util

for _name in (
    "sentence_transformers",
    "faiss",
    "retriv",
    "numba",
    "llama_cpp",
):
    if _name not in sys.modules and importlib.util.find_spec(_name) is None:
        sys.modules[_name] = _make_stub_module(_name)


# Now it's safe to import application code.
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api.routes.chatbot import router  # noqa: E402
from api.services import memory as memory_module  # noqa: E402
from tests.e2e.fixtures.stub_llm import StubLLMProvider  # noqa: E402


# ---------------------------------------------------------------------------
# Session data directory — redirect disk I/O to tmp_path
# ---------------------------------------------------------------------------

@pytest.fixture
def session_data_dir(tmp_path: Path, monkeypatch):
    """Point ``sessionmanager._SESSION_DIRECTORY`` at a per-test temp dir.

    The module-level variable is set once at import time from the
    ``SESSION_FILE_PATH`` env var.  Monkeypatching the already-resolved
    variable is the most reliable approach — no import-ordering issues.
    """
    data_dir = tmp_path / "sessions"
    data_dir.mkdir()

    import api.services.sessionmanager as sm
    monkeypatch.setattr(sm, "_SESSION_DIRECTORY", str(data_dir))

    yield data_dir

    # Cleanup (tmp_path is removed by pytest, but be explicit)
    shutil.rmtree(data_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Stub LLM — real object, no mock patching
# ---------------------------------------------------------------------------

@pytest.fixture
def stub_llm(monkeypatch):
    """Inject a ``StubLLMProvider`` into ``chat_service.llm_provider``.

    The production code path ``generate_answer() → llm_provider.generate()``
    executes normally; only inference is swapped.
    """
    provider = StubLLMProvider()
    monkeypatch.setattr(
        "api.services.chat_service.llm_provider", provider
    )
    return provider


# ---------------------------------------------------------------------------
# Dev-mode config — bypass RAG retrieval
# ---------------------------------------------------------------------------

@pytest.fixture
def dev_mode_config(monkeypatch):
    """Enable ``dev_mode`` in the loaded config so ``retrieve_context()``
    returns a placeholder instead of querying a FAISS index that doesn't
    exist in the test environment.
    """
    from api.config.loader import CONFIG
    monkeypatch.setitem(CONFIG, "dev_mode", True)


# ---------------------------------------------------------------------------
# FastAPI TestClient
# ---------------------------------------------------------------------------

@pytest.fixture
def e2e_app() -> FastAPI:
    """A bare FastAPI instance with the chatbot router mounted.

    We intentionally skip the ``lifespan`` handler (periodic cleanup task)
    to keep E2E tests fast and deterministic.
    """
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def e2e_client(
    e2e_app: FastAPI,
    session_data_dir,       # noqa: ARG001 — activates the monkeypatch
    stub_llm,               # noqa: ARG001 — activates the monkeypatch
    dev_mode_config,        # noqa: ARG001 — activates the monkeypatch
):  # pylint: disable=unused-argument
    """Yield a ``TestClient`` with all E2E patches active.

    Used as a context manager so Starlette flushes ``BackgroundTasks``
    (e.g. ``persist_session``) before assertions run.
    """
    # Reset in-memory session store so tests are isolated
    memory_module.reset_sessions()

    with TestClient(e2e_app) as client:
        yield client
