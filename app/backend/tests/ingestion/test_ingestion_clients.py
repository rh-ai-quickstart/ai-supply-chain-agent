"""Tests for ingestion client helpers."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, mock_open, patch

from clients.embedding_client import openai_embeddings_kwargs
from clients.llamastack_vector_store_client import LlamaStackVectorStoreClient


def test_openai_embeddings_kwargs_direct_maas_url(monkeypatch):
    monkeypatch.delenv("EMBED_BASE_URL", raising=False)
    kwargs = openai_embeddings_kwargs(
        llama_stack_url="http://llamastack:8321",
        embed_model="text-embedding",
        embed_base_url="https://maas.example.com",
        embed_api_key="secret",
    )
    assert kwargs["base_url"] == "https://maas.example.com/v1"
    assert kwargs["api_key"] == "secret"
    assert kwargs["model"] == "text-embedding"


def test_openai_embeddings_kwargs_llama_stack_default():
    kwargs = openai_embeddings_kwargs(
        llama_stack_url="http://llamastack:8321",
        embed_model="embed-model",
    )
    assert kwargs["base_url"] == "http://llamastack:8321/v1"
    assert kwargs["model"] == "embed-model"


@patch("clients.llamastack_vector_store_client.OpenAI")
def test_llamastack_vector_store_client_create_and_attach(mock_openai):
    client = MagicMock()
    vs = MagicMock()
    vs.id = "vs-1"
    client.vector_stores.create.return_value = vs
    uploaded = MagicMock()
    uploaded.id = "file-1"
    client.files.create.return_value = uploaded
    mock_openai.return_value = client

    with patch.dict(os.environ, {"LLAMA_STACK_URL": "http://stack:8321"}):
        svc = LlamaStackVectorStoreClient()
    assert svc.create_vector_store("kb") == "vs-1"

    with patch("builtins.open", mock_open(read_data=b"data")):
        file_id = svc.upload_file("/tmp/doc.txt", source="demo")
    assert file_id == "file-1"
    svc.attach_file_to_store("vs-1", "file-1")
    client.vector_stores.files.create.assert_called_once_with(
        vector_store_id="vs-1",
        file_id="file-1",
    )
