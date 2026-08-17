"""Ingest recent RSS headlines into the news vector store.

On each call:
1. Fetch headlines from the RSS feeds
2. Truncate to the most recent articles (to avoid an ever-growing vector store)
3. Upload each article as a text file to the news vector store

The ingestion is best-effort: if LlamaStack is unavailable the vector store
stays as-is and the RSS cache works for ``fetch_news``.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from clients.news_client import NewsClient
from services.news_vector_store_service import NewsVectorStoreService
from logging_config import getLogger

logger = getLogger(__name__)

# Keep only the N most recent articles in the vector store at any time.
_max_articles = 80
_vector_store_name = "supply-chain-news"


def ingest_news(
    llama: Optional[Any] = None,
    news_client: Optional[NewsClient] = None,
    news_store: Optional[NewsVectorStoreService] = None,
    *,
    max_articles: int = _max_articles,
    vector_store_id: Optional[str] = None,
    vector_store_name: str = _vector_store_name,
) -> dict[str, Any]:
    """Ingest recent RSS headlines into the news vector store.

    This is the entry-point intended to be called from a route handler or
    script.  It is idempotent in the sense that it always refreshes the
    entire store with the ``max_articles`` most recent headlines (old
    articles are implicitly dropped since LlamaStack overwrites the store
    contents on each batch of file attachments).

    Returns a summary dict, e.g.::

        {"ok": True, "ingested": 42, "vector_store_id": "vs-..."}

    Keys ``ok`` / ``error`` / ``ingested`` / ``vector_store_id`` /
    ``warnings`` are always present.
    """
    result: dict[str, Any] = {
        "ok": False,
        "error": None,
        "ingested": 0,
        "vector_store_id": None,
        "warnings": [],
    }

    # --- 1. Fetch headlines ------------------------------------------------
    client = news_client or NewsClient()
    items = client.fetch_headlines()
    if not items:
        result["error"] = "No headlines available to ingest"
        return result

    items = items[:max_articles]
    result["warnings"].append(f"fetched {len(items)} headlines from RSS feeds")

    # --- 2. Ensure vector store exists -------------------------------------
    vs = news_store or NewsVectorStoreService(llama)
    vs_id = vector_store_id or None
    if vs_id:
        vs._vector_store_id = vs_id
    if not vs._vector_store_id:
        try:
            vs.ensure_created(vector_store_name)
        except Exception as exc:
            result["error"] = f"Failed to create news vector store: {exc}"
            return result
    vs_id = vs.vector_store_id
    if not vs_id:
        result["error"] = "No news vector store available for ingestion"
        return result
    result["vector_store_id"] = vs_id

    # --- 3. Upload each article as a text file -----------------------------
    llama_client = llama
    if not llama_client:
        result["error"] = "No LlamaStack client provided"
        return result

    # Delete existing store contents so old articles are dropped.
    # The LlamaStack API doesn't support a "clear store" endpoint, so we
    # recreate the store atomically.
    try:
        old_id = vs_id
        vs_id = llama_client.create_vector_store(vector_store_name)
        try:
            llama_client.delete_vector_store(old_id)
        except Exception:
            pass  # already gone; best-effort
        vs._vector_store_id = vs_id
        result["warnings"].append(f"recreated vector store id={vs_id}")
    except Exception as exc:
        result["error"] = f"Failed to recreate vector store: {exc}"
        return result

    ingested = 0
    for idx, item in enumerate(items):
        try:
            text = _build_article_text(item)
            file_id = llama_client.upload_file_bytes(f"news_{idx}.txt", text.encode("utf-8"))
            llama_client.attach_file_to_vector_store(vs_id, file_id)
            ingested += 1
        except Exception as exc:
            result["warnings"].append(f"failed to ingest item {idx}: {exc}")
            logger.warning("NewsIngestionService: %s", exc)

    result["ok"] = True
    result["ingested"] = ingested
    result["vector_store_id"] = vs_id
    return result


def _build_article_text(item: dict[str, Any]) -> str:
    """Build a plain-text block from a single RSS headline dict."""
    title = item.get("title") or ""
    summary = item.get("summary") or ""
    source = item.get("source") or "News"
    published = item.get("published_at") or ""
    link = item.get("link") or ""

    parts = [f"Source: {source}", f"Title: {title}"]
    if published:
        parts.append(f"Published: {published}")
    if summary:
        # Strip very short boilerplate summaries
        cleaned = re.sub(r"\s+", " ", summary).strip()
        if len(cleaned) > 20:
            parts.append(f"Summary: {cleaned}")
    if link:
        parts.append(f"Link: {link}")

    return "\n".join(parts)
