"""Knowledge-base context retrieval for RAG (extracted from ``ChatService`` for SRP).

Prefers the LlamaStack vector store search (when the caller/UI selected a
knowledge base); falls back to the direct PGVector similarity search client
when no vector store is selected.
"""

from __future__ import annotations

from typing import Any, Optional

from logging_config import getLogger

logger = getLogger(__name__)


class RagContextProvider:
    def __init__(
        self,
        llama_stack_client: Any,
        vector_store_client: Optional[Any] = None,
    ) -> None:
        self._llama_stack_client = llama_stack_client
        self._vector_store_client = vector_store_client

    def get_context(self, query: str, vector_store_id: Optional[str] = None) -> str:
        """Return relevant knowledge-base context for *query*, or empty string."""
        vs_id = (vector_store_id or "").strip()
        if vs_id:
            return self._llama_stack_client.search_vector_store(vs_id, query, max_num_results=8)

        if self._vector_store_client is None:
            return ""
        try:
            docs = self._vector_store_client.similarity_search(query, k=3)
            return "\n\n".join(doc.page_content for doc in docs)
        # Broad catch: best-effort RAG retrieval (langchain/DB) may raise varied errors; degrade to no context.
        except Exception as exc:
            logger.warning("RagContextProvider: vector store retrieval failed: %s", exc)
            return ""
