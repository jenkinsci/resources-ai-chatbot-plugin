"""
Minimal FAISS index seeder for E2E tests.

Creates a 2-document FAISS index in a temporary directory so the RAG
retrieval path can execute without the full data pipeline.

For the Part-1 scaffolding PR this fixture is a **stub**: the smoke test
runs with ``dev_mode=True`` which bypasses RAG entirely.  The real seeding
logic will be wired up in Part 2 (#194) once the scaffolding is merged.
"""

import json
import os
from pathlib import Path

import pytest

# Two minimal documents that would normally come from the data pipeline.
_SEED_DOCUMENTS = [
    {
        "id": "seed-doc-001",
        "chunk_text": (
            "Jenkins Pipeline is a suite of plugins that supports "
            "implementing and integrating continuous delivery pipelines."
        ),
        "code_blocks": [],
        "source": "plugins",
    },
    {
        "id": "seed-doc-002",
        "chunk_text": (
            "The Jenkins distributed builds architecture uses a "
            "controller and multiple agents to run workloads."
        ),
        "code_blocks": [],
        "source": "docs",
    },
]


@pytest.fixture
def seed_documents(tmp_path: Path):
    """Write the seed documents to a JSON file under *tmp_path* and return
    the list for assertion convenience.

    The actual FAISS index creation (embedding + ``faiss.IndexFlatL2``)
    will be added in Part 2 when ``dev_mode`` bypass is removed for
    specific scenarios.
    """
    docs_path = tmp_path / "seed_chunks.json"
    docs_path.write_text(json.dumps(_SEED_DOCUMENTS), encoding="utf-8")
    return _SEED_DOCUMENTS
