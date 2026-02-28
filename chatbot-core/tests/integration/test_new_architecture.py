"""Integration tests for the new-architecture (agentic) pipeline.

Verifies that ``POST /sessions/{id}/message`` routes to
``get_chatbot_reply_new_architecture()`` when the
``use_new_architecture`` config flag is ``True``, and that the
old path is still used when the flag is ``False`` (default).

See issue #189.
"""

import pytest
from api.services import memory


@pytest.fixture(autouse=True)
def reset_memory_sessions():
    """Clear in-memory session store between tests."""
    memory.reset_sessions()


# ---------------------------------------------------------------------------
# Routing test — flag OFF (default)
# ---------------------------------------------------------------------------

def test_flag_off_uses_old_architecture(
    client,
    mock_llm_provider,
    mock_get_relevant_documents,
    mocker,
):
    """When ``use_new_architecture`` is False the old ``get_chatbot_reply``
    path must be used — ``get_chatbot_reply_new_architecture`` is never called.
    """
    mock_llm_provider.generate.return_value = "old-arch reply"
    mock_get_relevant_documents.return_value = (
        [{"id": "d1", "chunk_text": "ctx"}],
        [0.9],
    )

    spy_new = mocker.patch(
        "api.routes.chatbot.get_chatbot_reply_new_architecture",
        wraps=None,
    )

    session_id = client.post("/sessions").json()["session_id"]
    resp = client.post(
        f"/sessions/{session_id}/message",
        json={"message": "Hello"},
    )

    assert resp.status_code == 200
    assert resp.json()["reply"] == "old-arch reply"
    spy_new.assert_not_called()


# ---------------------------------------------------------------------------
# Routing test — flag ON
# ---------------------------------------------------------------------------

def test_flag_on_uses_new_architecture(
    client,
    mock_llm_provider,
    mocker,
):
    """When ``use_new_architecture`` is True the request must be routed
    through ``get_chatbot_reply_new_architecture``.

    The LLM mock returns a sequence of responses that drive the agentic
    pipeline to completion:

      1. Query classifier  →  ``"SIMPLE"``
      2. Retriever agent   →  invalid JSON (triggers default tool calls)
      3. Context relevance →  ``"Label: 1"``  (context is relevant)
      4. Final answer      →  ``"new-arch reply"``

    ``_execute_search_tools`` is patched to avoid FAISS / embedding deps.
    """
    from api.config.loader import CONFIG

    mocker.patch.dict(CONFIG, {"use_new_architecture": True})

    mock_llm_provider.generate.side_effect = [
        "SIMPLE",                   # 1 — query classifier
        "not valid json",           # 2 — retriever agent (fallback)
        "Label: 1",                 # 3 — context relevance
        "new-arch reply",           # 4 — final answer
    ]

    mocker.patch(
        "api.services.chat_service._execute_search_tools",
        return_value="Mocked retrieval context for testing.",
    )

    session_id = client.post("/sessions").json()["session_id"]
    resp = client.post(
        f"/sessions/{session_id}/message",
        json={"message": "What is Jenkins?"},
    )

    assert resp.status_code == 200
    assert resp.json()["reply"] == "new-arch reply"
    assert mock_llm_provider.generate.call_count == 4


# ---------------------------------------------------------------------------
# MULTI query path
# ---------------------------------------------------------------------------

def test_new_architecture_multi_query(
    client,
    mock_llm_provider,
    mocker,
):
    """When the query classifier returns ``MULTI``, the pipeline should
    split the query into sub-queries and answer each independently.

    Call sequence:
      1. Query classifier     →  ``"MULTI"``
      2. Sub-query splitter   →  ``"['sub1', 'sub2']"``
      ---- sub-query 1 ----
      3. Retriever agent      →  invalid JSON (fallback)
      4. Context relevance    →  ``"Label: 1"``
      5. Final answer (sub1)  →  ``"Answer for sub1"``
      ---- sub-query 2 ----
      6. Retriever agent      →  invalid JSON (fallback)
      7. Context relevance    →  ``"Label: 1"``
      8. Final answer (sub2)  →  ``"Answer for sub2"``
    """
    from api.config.loader import CONFIG

    mocker.patch.dict(CONFIG, {"use_new_architecture": True})

    mock_llm_provider.generate.side_effect = [
        "MULTI",                    # 1 — query classifier
        "['sub1', 'sub2']",         # 2 — sub-query splitter
        # --- sub-query 1 ---
        "not valid json",           # 3 — retriever agent (fallback)
        "Label: 1",                 # 4 — context relevance
        "Answer for sub1",          # 5 — final answer
        # --- sub-query 2 ---
        "not valid json",           # 6 — retriever agent (fallback)
        "Label: 1",                 # 7 — context relevance
        "Answer for sub2",          # 8 — final answer
    ]

    mocker.patch(
        "api.services.chat_service._execute_search_tools",
        return_value="Mocked retrieval context.",
    )

    session_id = client.post("/sessions").json()["session_id"]
    resp = client.post(
        f"/sessions/{session_id}/message",
        json={"message": "Explain pipelines and agents"},
    )

    assert resp.status_code == 200
    reply = resp.json()["reply"]
    assert "Answer for sub1" in reply
    assert "Answer for sub2" in reply
    assert mock_llm_provider.generate.call_count == 8


# ---------------------------------------------------------------------------
# Irrelevant context → fallback message
# ---------------------------------------------------------------------------

def test_new_architecture_irrelevant_context_returns_fallback(
    client,
    mock_llm_provider,
    mocker,
):
    """When the relevance scorer says the context is irrelevant
    (``Label: 0``) on every iteration, the pipeline should return
    a fallback "unable to respond" message.

    ``max_reformulate_iterations`` is 1 in the test config, so the loop
    runs twice (iteration -1 → 0, then 0 → 1 which equals max and exits).
    """
    from api.config.loader import CONFIG

    mocker.patch.dict(CONFIG, {"use_new_architecture": True})

    mock_llm_provider.generate.side_effect = [
        "SIMPLE",                   # 1 — query classifier
        # --- iteration 0 ---
        "not valid json",           # 2 — retriever agent (fallback)
        "Label: 0",                 # 3 — context NOT relevant
        # --- iteration 1 ---
        "not valid json",           # 4 — retriever agent (fallback)
        "Label: 0",                 # 5 — still NOT relevant
    ]

    mocker.patch(
        "api.services.chat_service._execute_search_tools",
        return_value="Unrelated context.",
    )

    session_id = client.post("/sessions").json()["session_id"]
    resp = client.post(
        f"/sessions/{session_id}/message",
        json={"message": "Something obscure"},
    )

    assert resp.status_code == 200
    reply = resp.json()["reply"]
    assert "unfortunately" in reply.lower() or "not able" in reply.lower()
