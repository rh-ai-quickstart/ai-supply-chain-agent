import logging
from typing import Optional

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

    def reply(self, user_input: str) -> dict:
        lowered = (user_input or "").lower()

        if any(keyword in lowered for keyword in _GUARDRAIL_KEYWORDS):
            return {"answer": _GUARDRAIL_RESPONSE}

        if self.route_service.is_route_query(user_input):
            return self.route_service.get_optimized_route(user_input)

        context = self._retrieve_context(user_input)
        answer = self.llama_stack_client.ask(user_input, context=context)
        return {"answer": answer}

    def _retrieve_context(self, query: str) -> str:
        """Return relevant knowledge-base context for *query*, or empty string."""
        if self.vector_store_client is None:
            return ""
        try:
            docs = self.vector_store_client.similarity_search(query, k=3)
            return "\n\n".join(doc.page_content for doc in docs)
        except Exception as exc:
            logger.warning("Vector store retrieval failed: %s", exc)
            return ""
