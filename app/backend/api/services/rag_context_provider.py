"""Knowledge-base context retrieval for RAG (extracted from ``ChatService`` for SRP).

Uses LlamaStack vector store search when the caller/UI selected a knowledge base.
"""

from __future__ import annotations

from typing import Any, Optional

from logging_config import getLogger

logger = getLogger(__name__)


class RagContextProvider:
    def __init__(self, llama_stack_client: Any) -> None:
        self._llama_stack_client = llama_stack_client

    def get_context(self, query: str, vector_store_id: Optional[str] = None) -> str:
        """Return relevant knowledge-base context for *query*, or empty string."""
        vs_id = (vector_store_id or "").strip()
        if not vs_id:
            return ""
        try:
            return self._llama_stack_client.search_vector_store(vs_id, query, max_num_results=8)
        except Exception as exc:
            logger.warning("RagContextProvider: vector store retrieval failed: %s", exc)
            return ""
