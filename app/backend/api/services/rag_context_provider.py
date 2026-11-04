"""Knowledge-base context retrieval for RAG (extracted from ``ChatService`` for SRP).

Uses LlamaStack vector store search when the caller/UI selected a knowledge base.
"""

from __future__ import annotations

from contextlib import nullcontext
from typing import Any, Optional

from logging_config import getLogger

logger = getLogger(__name__)


class RagContextProvider:
    def __init__(self, llama_stack_client: Any, tracing: Any = None) -> None:
        self._llama_stack_client = llama_stack_client
        self._tracing = tracing

    def get_context(self, query: str, vector_store_id: Optional[str] = None) -> str:
        """Return relevant knowledge-base context for *query*, or empty string."""
        vs_id = (vector_store_id or "").strip()
        if not vs_id:
            return ""
        span_context = (
            self._tracing.span(
                name="knowledge_base.search",
                span_type="RETRIEVER",
                inputs={"query": query, "vector_store_id": vs_id},
            )
            if self._tracing is not None
            else nullcontext(None)
        )
        with span_context as span:
            try:
                context = self._llama_stack_client.search_vector_store(
                    vs_id, query, max_num_results=8
                )
            except Exception as exc:
                logger.warning("RagContextProvider: vector store retrieval failed: %s", exc)
                context = ""

            if span is not None:
                chunks = (
                    [
                        {
                            "page_content": context,
                            "metadata": {"vector_store_id": vs_id},
                        }
                    ]
                    if context
                    else []
                )
                span.set_outputs(chunks)
            return context
