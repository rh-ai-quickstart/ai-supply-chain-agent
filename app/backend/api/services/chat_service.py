import logging
from typing import Any, Optional

from clients.llama_stack_client import LlamaStackClient
from clients.vector_store_client import VectorStoreClient
from services.route_service import RouteService

logger = logging.getLogger(__name__)

_GUARDRAIL_KEYWORDS = [
    "restaurant",
    "food",
    "weather",
    "sports",
    "movie",
    "pizza",
    "burger",
    "joke",
    "politics",
]

_GUARDRAIL_RESPONSE = (
    "I am restricted to supply chain topics only. "
    "Please ask about logistics, demand, routing, or risk."
)


class ChatService:
    def __init__(
        self,
        llama_stack_client: LlamaStackClient,
        route_service: RouteService,
        vector_store_client: Optional[VectorStoreClient] = None,
    ):
        self.llama_stack_client = llama_stack_client
        self.route_service = route_service
        self.vector_store_client = vector_store_client

    def reply(
        self,
        user_input: str,
        chat_history: Optional[list[dict[str, Any]]] = None,
        vector_store_id: Optional[str] = None,
    ) -> dict:
        history = chat_history if isinstance(chat_history, list) else []
        latest = self._latest_user_text(history, user_input)
        lowered = (latest or "").lower()

        if any(keyword in lowered for keyword in _GUARDRAIL_KEYWORDS):
            return {"answer": _GUARDRAIL_RESPONSE}

        if self.route_service.is_route_query(latest):
            return self.route_service.get_optimized_route(latest)

        context = self._retrieve_context(latest, vector_store_id=vector_store_id)
        conversation = self._map_chat_history(history)
        answer = self.llama_stack_client.ask(
            latest,
            context=context,
            conversation_messages=conversation,
        )
        logger.info("ChatService: answer: %s", answer)
        return {"answer": answer}

    @staticmethod
    def _latest_user_text(history: list[dict[str, Any]], fallback: str) -> str:
        for entry in reversed(history):
            if entry.get("role") == "human" and (entry.get("content") or "").strip():
                return str(entry["content"]).strip()
        return (fallback or "").strip()

    @staticmethod
    def _map_chat_history(history: list[dict[str, Any]]) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for entry in history:
            role = entry.get("role")
            content = (entry.get("content") or "").strip()
            if not content:
                continue
            if role == "human":
                out.append({"role": "user", "content": content})
            elif role == "ai":
                out.append({"role": "assistant", "content": content})
        return out

    def _retrieve_context(self, query: str, vector_store_id: Optional[str] = None) -> str:
        """Return relevant knowledge-base context for *query*, or empty string."""
        vs_id = (vector_store_id or "").strip()
        if vs_id:
            return self.llama_stack_client.search_vector_store(vs_id, query, max_num_results=8)

        if self.vector_store_client is None:
            return ""
        try:
            docs = self.vector_store_client.similarity_search(query, k=3)
            return "\n\n".join(doc.page_content for doc in docs)
        except Exception as exc:
            logger.warning("Vector store retrieval failed: %s", exc)
            return ""

    def list_vector_stores(self) -> list[dict[str, Any]]:
        """Expose LlamaStack vector stores for the chat UI."""
        return self.llama_stack_client.list_vector_stores()
