"""Tests for ``services.news_vector_store_service``."""

from __future__ import annotations

from unittest.mock import MagicMock

from services.news_vector_store_service import NewsVectorStoreService


def test_search_returns_empty_without_store_id():
    llama = MagicMock()
    service = NewsVectorStoreService(llama)
    assert service.search("port congestion") == ""


def test_search_delegates_to_llama_client():
    llama = MagicMock()
    llama.search_vector_store.return_value = "Article about ports."
    service = NewsVectorStoreService(llama)
    service._vector_store_id = "vs-news"
    out = service.search("  port congestion  ", max_results=3)
    assert out == "Article about ports."
    llama.search_vector_store.assert_called_once_with(
        "vs-news", "port congestion", max_num_results=3
    )


def test_ensure_created_skips_when_id_already_set():
    llama = MagicMock()
    service = NewsVectorStoreService(llama)
    service._vector_store_id = "existing"
    service.ensure_created()
    llama.create_vector_store.assert_not_called()


def test_ensure_created_without_llama_client():
    service = NewsVectorStoreService(None)
    service.ensure_created()
    assert service.vector_store_id is None


def test_ensure_created_sets_id_on_success():
    llama = MagicMock()
    llama.create_vector_store.return_value = "vs-new"
    service = NewsVectorStoreService(llama)
    service.ensure_created("custom-news")
    assert service.vector_store_id == "vs-new"
    llama.create_vector_store.assert_called_once_with("custom-news")


def test_ensure_created_handles_create_failure():
    llama = MagicMock()
    llama.create_vector_store.side_effect = RuntimeError("llama down")
    service = NewsVectorStoreService(llama)
    service.ensure_created()
    assert service.vector_store_id is None
