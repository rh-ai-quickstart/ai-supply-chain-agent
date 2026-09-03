"""Tests for ``clients.llama_vector_store_admin``."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from clients.llama_vector_store_admin import LlamaStackVectorStoreAdmin
from openai import APIError


def _admin() -> tuple[LlamaStackVectorStoreAdmin, MagicMock]:
    client = MagicMock()
    return LlamaStackVectorStoreAdmin(client, vector_store_provider="pgvector"), client


def test_list_vector_stores_maps_response():
    admin, client = _admin()
    vs = MagicMock()
    vs.id = "vs-1"
    vs.name = "news"
    vs.status = "ready"
    vs.created_at = 123
    page = MagicMock()
    page.data = [vs]
    client.vector_stores.list.return_value = page

    out = admin.list_vector_stores()
    assert out == [
        {"id": "vs-1", "name": "news", "status": "ready", "created_at": 123}
    ]


def test_list_vector_stores_api_error_returns_empty():
    admin, client = _admin()
    client.vector_stores.list.side_effect = APIError(
        "fail", request=MagicMock(), body=None
    )
    assert admin.list_vector_stores() == []


def test_search_vector_store_concatenates_chunks():
    admin, client = _admin()
    block = MagicMock()
    block.type = "text"
    block.text = "  Port congestion  "
    row = MagicMock()
    row.content = [block]
    page = MagicMock()
    page.data = [row]
    client.vector_stores.search.return_value = page

    out = admin.search_vector_store("vs-1", "ports", max_num_results=5)
    assert out == "Port congestion"
    client.vector_stores.search.assert_called_once()


def test_search_vector_store_empty_query():
    admin, _ = _admin()
    assert admin.search_vector_store("vs-1", "   ") == ""


def test_create_vector_store():
    admin, client = _admin()
    created = MagicMock()
    created.id = "vs-new"
    client.vector_stores.create.return_value = created
    assert admin.create_vector_store("kb-1") == "vs-new"
    client.vector_stores.create.assert_called_once_with(
        name="kb-1",
        extra_body={"provider_id": "pgvector"},
    )


def test_upload_and_attach_file():
    admin, client = _admin()
    uploaded = MagicMock()
    uploaded.id = "file-1"
    client.files.create.return_value = uploaded
    assert admin.upload_file_bytes("doc.txt", b"hello") == "file-1"
    admin.attach_file_to_vector_store("vs-1", "file-1")
    client.vector_stores.files.create.assert_called_once_with(
        vector_store_id="vs-1",
        file_id="file-1",
    )


def test_delete_vector_store_swallows_errors():
    admin, client = _admin()
    client.vector_stores.delete.side_effect = RuntimeError("gone")
    admin.delete_vector_store("vs-1")  # should not raise
