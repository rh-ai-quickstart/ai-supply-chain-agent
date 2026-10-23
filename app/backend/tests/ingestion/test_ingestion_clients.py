"""Tests for ingestion client helpers."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, mock_open, patch

from clients.llamastack_vector_store_client import LlamaStackVectorStoreClient


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
