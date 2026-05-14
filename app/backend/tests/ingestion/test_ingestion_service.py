"""``IngestionService.run`` without importing LangChain / PGVector."""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest


def _stub_clients_vector_store() -> None:
    if "clients.vector_store_client" in sys.modules:
        return
    mod = types.ModuleType("clients.vector_store_client")

    class VectorStoreClient:  # noqa: D401
        """Stub; real client pulls LangChain + PG."""

    mod.VectorStoreClient = VectorStoreClient
    sys.modules["clients.vector_store_client"] = mod
    pkg = types.ModuleType("clients")
    sys.modules["clients"] = pkg


def _stub_loaders_document() -> None:
    if "loaders.document_loader" in sys.modules:
        return
    mod = types.ModuleType("loaders.document_loader")

    class DocumentLoader:  # noqa: D401
        """Stub; real loader pulls LangChain document loaders."""

    mod.DocumentLoader = DocumentLoader
    sys.modules["loaders.document_loader"] = mod
    pkg = types.ModuleType("loaders")
    sys.modules["loaders"] = pkg


@pytest.fixture(scope="module", autouse=True)
def ingestion_service_module():
    _stub_clients_vector_store()
    _stub_loaders_document()
    import importlib

    name = "services.ingestion_service"
    sys.modules.pop(name, None)
    return importlib.import_module(name)


def test_run_passes_chunks_to_vector_store(ingestion_service_module):
    IngestionService = ingestion_service_module.IngestionService
    from config import IngestConfig, IngestionStrategy

    vs = MagicMock()
    loader = MagicMock()
    loader.load_and_split.return_value = ["chunk-a", "chunk-b"]
    svc = IngestionService(vs, loader)
    cfg = IngestConfig(
        strategy=IngestionStrategy.LANGCHAIN,
        knowledge_base_dir="kb",
        drop_old=True,
    )
    n = svc.run(cfg)
    assert n == 2
    loader.load_and_split.assert_called_once_with("kb")
    vs.add_documents.assert_called_once_with(["chunk-a", "chunk-b"], drop_old=True)
