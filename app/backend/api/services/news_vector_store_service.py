"""Service to create, manage, and search a dedicated vector store for news articles.

Uses LlamaStack's OpenAI-compatible vector store API under the hood. Each
article is uploaded as a small text file so LlamaStack performs server-side
chunking and embedding.
"""

from __future__ import annotations

import logging
from typing import Optional

from clients.llama_stack_client import LlamaStackClient

logger = logging.getLogger(__name__)

_NEWS_VECTOR_STORE_NAME = "supply-chain-news"


class NewsVectorStoreService:
    """Manage a persistent vector store that holds recent news articles."""

    def __init__(self, llama_client: Optional[LlamaStackClient] = None) -> None:
        self._llama = llama_client
        self._vector_store_id: Optional[str] = None

    @property
    def vector_store_id(self) -> Optional[str]:
        return self._vector_store_id

    def search(self, query: str, max_results: int = 5) -> str:
        """Search the news vector store and return concatenated matching chunks."""
        if not self._vector_store_id:
            return ""
        if not self._llama:
            return ""
        return self._llama.search_vector_store(
            self._vector_store_id,
            query.strip(),
            max_num_results=max_results,
        )

    def ensure_created(self, name: str = _NEWS_VECTOR_STORE_NAME) -> None:
        """Create the news vector store if it does not already exist.

        Only sets ``self._vector_store_id`` when creation succeeds.
        """
        if self._vector_store_id:
            return
        if not self._llama:
            logger.warning("NewsVectorStoreService: no LlamaStack client; cannot create news vector store")
            return
        try:
            self._vector_store_id = self._llama.create_vector_store(name)
            logger.info("NewsVectorStoreService: news vector store created id=%s", self._vector_store_id)
        except Exception as exc:
            logger.warning("NewsVectorStoreService: failed to create news vector store: %s", exc)
