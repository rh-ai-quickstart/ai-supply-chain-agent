"""Tests for ``services.news_ingestion_service``."""

from __future__ import annotations

from unittest.mock import MagicMock

from services.news_ingestion_service import _build_article_text, ingest_news


def test_build_article_text_includes_title_and_summary():
    text = _build_article_text(
        {
            "title": "Port strike",
            "summary": "Workers walk out at LA port.",
            "source": "Reuters",
            "published_at": "2026-01-01",
            "link": "https://example.com/story",
        }
    )
    assert "Port strike" in text
    assert "Workers walk out" in text
    assert "Reuters" in text


def test_ingest_news_no_headlines():
    news_client = MagicMock()
    news_client.fetch_headlines.return_value = []
    result = ingest_news(news_client=news_client, llama=MagicMock())
    assert result["ok"] is False
    assert result["error"] == "No headlines available to ingest"


def test_ingest_news_no_llama_client():
    news_client = MagicMock()
    news_client.fetch_headlines.return_value = [{"title": "Headline", "source": "News"}]
    llama = MagicMock()
    llama.create_vector_store.return_value = "vs-1"
    news_store = MagicMock()
    news_store._vector_store_id = "vs-1"
    news_store.vector_store_id = "vs-1"

    result = ingest_news(
        llama=None,
        news_client=news_client,
        news_store=news_store,
    )
    assert result["ok"] is False
    assert "LlamaStack" in result["error"]


def test_ingest_news_success():
    news_client = MagicMock()
    news_client.fetch_headlines.return_value = [
        {"title": "Strike", "source": "News", "summary": "Long enough summary text here."},
    ]
    llama = MagicMock()
    llama.create_vector_store.return_value = "vs-new"
    llama.upload_file_bytes.return_value = "file-1"
    news_store = MagicMock()
    news_store._vector_store_id = None
    news_store.vector_store_id = None

    def _ensure(name="supply-chain-news"):
        news_store._vector_store_id = "vs-old"
        news_store.vector_store_id = "vs-old"

    news_store.ensure_created.side_effect = _ensure

    result = ingest_news(
        llama=llama,
        news_client=news_client,
        news_store=news_store,
        max_articles=10,
    )
    assert result["ok"] is True
    assert result["ingested"] == 1
    assert result["vector_store_id"] == "vs-new"
    llama.attach_file_to_vector_store.assert_called_once_with("vs-new", "file-1")
