import io
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

    @staticmethod
    def _completion_to_json(completion: Any) -> dict[str, Any]:
        """Serialize an OpenAI ``ChatCompletion`` (or similar) for API responses."""
        if completion is None:
            return {}
        try:
            dumped = completion.model_dump(mode="json")
            return dumped if isinstance(dumped, dict) else {"value": dumped}
        except Exception as exc:
            logger.warning("LlamaStackClient: could not model_dump completion: %s", exc)
            return {"serialization_error": str(exc)}

    def ask(
        self,
        user_input: str,
        context: str = "",
        conversation_messages: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Call the chat completion API.

        Returns a dict with ``answer`` (assistant text) and ``completion`` (full
        JSON-serializable completion payload from the stack, including ``usage``).
        """
        if not self.base_url:
            return {
                "answer": "Something went wrong. There is no endpoint configured.",
                "completion": None,
            }

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
            text = completion.choices[0].message.content or "Darn! Something went wrong."
            return {
                "answer": text,
                "completion": self._completion_to_json(completion),
            }
        except Exception as exc:
            logger.error("Llama Stack request failed: %s", exc)
            return {
                "answer": f"Darn! Something went wrong: {exc}",
                "completion": None,
            }

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

    def create_vector_store(self, name: str) -> str:
        """Create a LlamaStack vector store; returns the server-assigned id."""
        provider = os.getenv("VECTOR_STORE_PROVIDER", "pgvector")
        vector_store = self._client.vector_stores.create(
            name=name,
            extra_body={"provider_id": provider},
        )
        logger.info("LlamaStackClient: created vector store id=%s name=%s", vector_store.id, name)
        return str(vector_store.id)

    def upload_file_bytes(self, filename: str, content: bytes) -> str:
        """Upload file bytes to LlamaStack; returns file id."""
        buffer = io.BytesIO(content)
        response = self._client.files.create(
            file=(filename, buffer),
            purpose="assistants",
        )
        logger.info("LlamaStackClient: uploaded file id=%s name=%s", response.id, filename)
        return str(response.id)

    def attach_file_to_vector_store(self, vector_store_id: str, file_id: str) -> None:
        """Attach an uploaded file to a vector store (triggers server-side chunk/embed)."""
        self._client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_id,
        )
        logger.info(
            "LlamaStackClient: attached file_id=%s to vector_store_id=%s",
            file_id,
            vector_store_id,
        )
