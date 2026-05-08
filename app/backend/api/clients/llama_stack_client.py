import logging
import os
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an AI assistant for a supply chain command center. "
    "You help operators understand logistics data, demand forecasting, "
    "inventory levels, supplier risk, and shipping routes. "
    "Answer concisely and only about supply chain topics. "
    "If asked about unrelated topics, politely redirect to supply chain matters."
)


class LlamaStackClient:
    """OpenAI-compatible client pointed at a Llama Stack server."""

    def __init__(self, timeout_seconds: int = 30):
        self.base_url = os.getenv(
            "LLAMA_STACK_URL", "http://llamastack:8321"
        ).rstrip("/") + "/v1/openai/v1"
        self.model = os.getenv(
            "LLAMA_STACK_MODEL",
            "meta-llama/Llama-3.2-1B-Instruct",
        )
        self._timeout = timeout_seconds

        self._client = OpenAI(
            api_key="not-required",
            base_url=self.base_url,
        )
        logger.info(
            "LlamaStackClient: base_url=%s model=%s (set LLAMA_STACK_MODEL to match "
            "a model id served by this stack, e.g. remote-llm from Helm global.models)",
            self.base_url,
            self.model,
        )

    def ask(
        self,
        user_input: str,
        context: str = "",
        conversation_messages: list[dict] | None = None,
    ) -> str:
        """Send *user_input* to the LLM and return the text response.

        Args:
            user_input: The user's latest question or message (also used when
                *conversation_messages* is empty).
            context:    Optional RAG context retrieved from the vector store.
                        When provided it is injected as a system message before
                        the user turn so the model can ground its answer.
            conversation_messages: Optional OpenAI-style turns (``user`` /
                ``assistant``) built from prior chat, including the latest user
                message when applicable.
        """
        if not self.base_url:
            return "Something went wrong. There is no endpoint configured."

        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

        if context:
            messages.append(
                {
                    "role": "system",
                    "content": f"Relevant context from the knowledge base:\n{context}",
                }
            )

        turns = conversation_messages if conversation_messages else []
        if turns:
            messages.extend(turns)
        else:
            messages.append({"role": "user", "content": user_input})

        try:
            completion = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
                timeout=self._timeout,
            )
            logger.info("LlamaStackClient: completion: %s", completion)
            return completion.choices[0].message.content or "Darn! Something went wrong."
        except Exception as exc:
            logger.error("Llama Stack request failed: %s", exc)
            return f"Darn! Something went wrong: {exc}"

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
        except Exception as exc:
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
        except Exception as exc:
            logger.warning(
                "LlamaStack vector_stores.search failed store=%s: %s",
                vector_store_id,
                exc,
            )
            return ""
