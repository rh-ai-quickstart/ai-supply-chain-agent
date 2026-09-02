"""Tests for ``clients.vector_store_client``."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from clients.vector_store_client import VectorStoreClient


def test_init_requires_password():
    with pytest.raises(RuntimeError, match="PG_PASSWORD"):
        VectorStoreClient(password=None)


@patch("clients.vector_store_client.PGVector")
@patch("clients.vector_store_client.OpenAIEmbeddings")
@patch("clients.vector_store_client.openai_embeddings_kwargs")
def test_similarity_search_delegates(mock_embed_kwargs, mock_embeddings, mock_pgvector):
    mock_embed_kwargs.return_value = {"api_key": "k", "base_url": "http://x/v1", "model": "m"}
    store = MagicMock()
    doc = MagicMock()
    store.similarity_search.return_value = [doc]
    mock_pgvector.return_value = store

    client = VectorStoreClient(password="secret")
    out = client.similarity_search("supply chain risk", k=5)

    assert out == [doc]
    store.similarity_search.assert_called_once_with("supply chain risk", k=5)
    mock_pgvector.assert_called_once()
    mock_embeddings.assert_called_once()
