"""Vector store administration against an OpenAI-compatible LlamaStack endpoint.

Split out of the former monolithic ``LlamaStackClient`` (SRP + ISP): consumers
that only need vector-store CRUD/search (e.g. knowledge-base ingest) don't
need to depend on the chat-completion or tool-loop surfaces.
"""

from __future__ import annotations

import io
import logging
from typing import Any

from openai import APIError, OpenAI

logger = logging.getLogger(__name__)


class LlamaStackVectorStoreAdmin:
    """Create/search/delete vector stores and manage their file attachments."""

    def __init__(self, client: OpenAI, *, vector_store_provider: str = "pgvector"):
        self._client = client
        self._provider = vector_store_provider

    def list_vector_stores(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return vector stores from LlamaStack (OpenAI-compatible ``/vector_stores``)."""
        out: list[dict[str, Any]] = []
        try:
            page = self._client.vector_stores.list(limit=min(limit, 100), order="desc")
            for vs in page.data:
                out.append(
                    {
                        "id": vs.id,
                        "name": vs.name or vs.id,
                        "status": getattr(vs, "status", None),
                        "created_at": vs.created_at,
                    }
                )
        except APIError as exc:
            logger.warning("LlamaStack list vector_stores failed: %s", exc)
        return out

    def search_vector_store(
        self,
        vector_store_id: str,
        query: str,
        *,
        max_num_results: int = 8,
    ) -> str:
        """Run vector store search; returns concatenated chunk text for RAG."""
        if not vector_store_id or not (query or "").strip():
            return ""
        try:
            page = self._client.vector_stores.search(
                vector_store_id,
                query=query.strip(),
                max_num_results=min(max(max_num_results, 1), 50),
            )
            parts: list[str] = []
            for row in page.data:
                for block in row.content:
                    if getattr(block, "type", None) == "text":
                        text = getattr(block, "text", "") or ""
                        if text.strip():
                            parts.append(text.strip())
            return "\n\n".join(parts)
        except APIError as exc:
            logger.warning(
                "LlamaStack vector_stores.search failed store=%s: %s",
                vector_store_id,
                exc,
            )
            return ""

    def create_vector_store(self, name: str) -> str:
        """Create a LlamaStack vector store; returns the server-assigned id."""
        vector_store = self._client.vector_stores.create(
            name=name,
            extra_body={"provider_id": self._provider},
        )
        logger.info("LlamaStackVectorStoreAdmin: created vector store id=%s name=%s", vector_store.id, name)
        return str(vector_store.id)

    def upload_file_bytes(self, filename: str, content: bytes) -> str:
        """Upload file bytes to LlamaStack; returns file id."""
        buffer = io.BytesIO(content)
        response = self._client.files.create(
            file=(filename, buffer),
            purpose="assistants",
        )
        logger.info("LlamaStackVectorStoreAdmin: uploaded file id=%s name=%s", response.id, filename)
        return str(response.id)

    def attach_file_to_vector_store(self, vector_store_id: str, file_id: str) -> None:
        """Attach an uploaded file to a vector store (triggers server-side chunk/embed)."""
        self._client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_id,
        )
        logger.info(
            "LlamaStackVectorStoreAdmin: attached file_id=%s to vector_store_id=%s",
            file_id,
            vector_store_id,
        )

    def delete_vector_store(self, vector_store_id: str) -> None:
        """Delete a vector store by id. Used for cleanup on partial ingestion failure."""
        try:
            self._client.vector_stores.delete(vector_store_id)
            logger.info("LlamaStackVectorStoreAdmin: deleted vector store id=%s", vector_store_id)
        except Exception as exc:
            logger.warning(
                "LlamaStackVectorStoreAdmin: failed to delete vector store id=%s: %s",
                vector_store_id,
                exc,
            )
