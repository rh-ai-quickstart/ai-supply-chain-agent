"""Tests for ``ingestion.loaders.document_loader``."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _import_document_loader():
    """Import DocumentLoader after stubbing heavy LangChain dependencies."""
    for name in (
        "langchain_community",
        "langchain_community.document_loaders",
        "langchain_text_splitters",
    ):
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)
    sys.modules["langchain_community.document_loaders"].DirectoryLoader = MagicMock()
    sys.modules["langchain_community.document_loaders"].TextLoader = MagicMock()
    sys.modules["langchain_text_splitters"].RecursiveCharacterTextSplitter = MagicMock

    sys.modules.pop("loaders.document_loader", None)
    return importlib.import_module("loaders.document_loader")


@pytest.fixture(scope="module")
def document_loader_module():
    return _import_document_loader()


def test_load_and_split_missing_directory(document_loader_module, tmp_path):
    DocumentLoader = document_loader_module.DocumentLoader
    loader = DocumentLoader()
    with pytest.raises(FileNotFoundError, match="Knowledge base directory not found"):
        loader.load_and_split(str(tmp_path / "missing"))


def test_load_and_split_no_documents(document_loader_module, tmp_path):
    DocumentLoader = document_loader_module.DocumentLoader
    path = tmp_path / "kb"
    path.mkdir()
    instance = MagicMock()
    instance.load.return_value = []
    document_loader_module.DirectoryLoader.return_value = instance

    loader = DocumentLoader()
    with pytest.raises(ValueError, match="No documents matched"):
        loader.load_and_split(str(path))


def test_load_and_split_returns_chunks(document_loader_module, tmp_path):
    DocumentLoader = document_loader_module.DocumentLoader
    path = tmp_path / "kb"
    path.mkdir()
    raw_doc = MagicMock()
    instance = MagicMock()
    instance.load.return_value = [raw_doc]
    document_loader_module.DirectoryLoader.return_value = instance

    loader = DocumentLoader(chunk_size=100, chunk_overlap=10)
    loader._splitter = MagicMock()
    loader._splitter.split_documents.return_value = ["chunk-1", "chunk-2"]

    chunks = loader.load_and_split(str(path))
    assert chunks == ["chunk-1", "chunk-2"]
    loader._splitter.split_documents.assert_called_once_with([raw_doc])
