import logging
from collections.abc import Iterator
from dataclasses import dataclass
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


@dataclass(frozen=True)
class _PreparedChatTurn:
    """Normalized inputs shared by sync and streaming reply paths."""

    latest: str
    history: list[dict[str, Any]]
    client: LlamaStackClient
    context: str
    conversation: list[dict[str, str]]


class ChatService:
    def __init__(
        self,
        llama_stack_client: LlamaStackClient,
        route_service: RouteService,
        vector_store_client: Optional[VectorStoreClient] = None,
        openai_client: Optional[LlamaStackClient] = None,
    ):
        self.llama_stack_client = llama_stack_client
        self.openai_client: LlamaStackClient = openai_client or llama_stack_client
        self.route_service = route_service
        self.vector_store_client = vector_store_client

    def reply(
        self,
        user_input: str,
        chat_history: Optional[list[dict[str, Any]]] = None,
        vector_store_id: Optional[str] = None,
        use_vllm: bool = True,
    ) -> dict:
        shortcut = self._early_reply(user_input, chat_history)
        if shortcut is not None:
            return shortcut

        turn = self._prepare_llm_turn(user_input, chat_history, vector_store_id, use_vllm)
        self._log_llm_routing(turn.client, use_vllm, streaming=False)
        llm_result = turn.client.ask(
            turn.latest,
            context=turn.context,
            conversation_messages=turn.conversation,
        )
        answer = llm_result.get("answer", "")
        logger.info(
            "ChatService: answer received from LlamaStack[%s] model=%s",
            turn.client.label,
            turn.client.model,
        )
        return {
            "answer": answer,
            "completion": llm_result.get("completion"),
        }

    def reply_stream(
        self,
        user_input: str,
        chat_history: Optional[list[dict[str, Any]]] = None,
        vector_store_id: Optional[str] = None,
        use_vllm: bool = True,
    ) -> Iterator[dict[str, Any]]:
        """Yield SSE-friendly chat events (guardrails, route shortcuts, or LLM stream)."""
        shortcut = self._early_reply(user_input, chat_history)
        if shortcut is not None:
            yield {"type": "done", **shortcut}
            return

        turn = self._prepare_llm_turn(user_input, chat_history, vector_store_id, use_vllm)
        self._log_llm_routing(turn.client, use_vllm, streaming=True)
        yield from turn.client.ask_stream(
            turn.latest,
            context=turn.context,
            conversation_messages=turn.conversation,
        )

    def _early_reply(
        self,
        user_input: str,
        chat_history: Optional[list[dict[str, Any]]],
    ) -> Optional[dict[str, Any]]:
        """Return a guardrail or route shortcut response, or ``None`` to call the LLM."""
        history = chat_history if isinstance(chat_history, list) else []
        latest = self._latest_user_text(history, user_input)
        lowered = (latest or "").lower()

        if any(keyword in lowered for keyword in _GUARDRAIL_KEYWORDS):
            return {"answer": _GUARDRAIL_RESPONSE, "completion": None}

        if self.route_service.is_route_query(latest):
            out = dict(self.route_service.get_optimized_route(latest))
            out.setdefault("completion", None)
            return out

        return None

    def _prepare_llm_turn(
        self,
        user_input: str,
        chat_history: Optional[list[dict[str, Any]]],
        vector_store_id: Optional[str],
        use_vllm: bool,
    ) -> _PreparedChatTurn:
        history = chat_history if isinstance(chat_history, list) else []
        latest = self._latest_user_text(history, user_input)
        client = self.llama_stack_client if use_vllm else self.openai_client
        context = self._retrieve_context(latest, vector_store_id=vector_store_id)
        conversation = self._map_chat_history(history)
        return _PreparedChatTurn(
            latest=latest,
            history=history,
            client=client,
            context=context,
            conversation=conversation,
        )

    @staticmethod
    def _log_llm_routing(client: LlamaStackClient, use_vllm: bool, *, streaming: bool) -> None:
        mode = "streaming" if streaming else "routing"
        logger.info(
            "ChatService: %s request to LlamaStack[%s] model=%s base_url=%s (use_vllm=%s)",
            mode,
            client.label,
            client.model,
            client.base_url,
            use_vllm,
        )

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
