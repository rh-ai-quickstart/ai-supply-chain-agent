import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Optional

from clients.llama_stack_client import LlamaStackClient
from clients.vector_store_client import VectorStoreClient
from services.agent_service import AgentService
from services.route_service import RouteService
from services.simulation_intent import is_simulation_intent, resolve_scenario_id

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

_SIMULATION_NEEDS_SCENARIO = (
    "I can run an impact simulation, but I need an active scenario. "
    "Select a scenario in Impact Query (UK Airspace Closure, Port Strike LA, or Suez Blockage), "
    "or mention one in your question."
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
        agent_service: Optional[AgentService] = None,
    ):
        self.llama_stack_client = llama_stack_client
        self.openai_client: LlamaStackClient = openai_client or llama_stack_client
        self.route_service = route_service
        self.vector_store_client = vector_store_client
        self.agent_service = agent_service or AgentService(llama_stack_client)

    def reply(
        self,
        user_input: str,
        chat_history: Optional[list[dict[str, Any]]] = None,
        vector_store_id: Optional[str] = None,
        use_vllm: bool = True,
        scenario_id: Optional[str] = None,
    ) -> dict:
        shortcut = self._early_reply(user_input, chat_history, scenario_id=scenario_id)
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
        scenario_id: Optional[str] = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield SSE-friendly chat events (guardrails, route/sim shortcuts, or LLM stream)."""
        shortcut = self._early_reply(user_input, chat_history, scenario_id=scenario_id)
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
        scenario_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Return a guardrail, route, or simulation shortcut, or ``None`` to call the LLM."""
        history = chat_history if isinstance(chat_history, list) else []
        latest = self._latest_user_text(history, user_input)
        lowered = (latest or "").lower()

        if any(keyword in lowered for keyword in _GUARDRAIL_KEYWORDS):
            return {"answer": _GUARDRAIL_RESPONSE, "completion": None}

        if self.route_service.is_route_query(latest):
            out = dict(self.route_service.get_optimized_route(latest))
            out.setdefault("completion", None)
            return out

        sim = self._maybe_run_simulation_tool(latest, scenario_id=scenario_id)
        if sim is not None:
            return sim

        return None

    def _maybe_run_simulation_tool(
        self,
        latest: str,
        scenario_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        if not is_simulation_intent(latest):
            return None

        resolved = resolve_scenario_id(latest, preferred=scenario_id)
        if not resolved:
            return {"answer": _SIMULATION_NEEDS_SCENARIO, "completion": None}

        logger.info(
            "ChatService: invoking general_simulation tool scenario_id=%s",
            resolved,
        )
        tool_result = self.agent_service.run_tool(
            "general_simulation",
            question=latest,
            scenario_id=resolved,
        )
        if not tool_result.success:
            return {
                "answer": (
                    "I tried to run the impact simulation tool but it failed: "
                    f"{tool_result.error or 'unknown error'}"
                ),
                "completion": None,
            }

        simulation = tool_result.data if isinstance(tool_result.data, dict) else {}
        answer = (
            simulation.get("answer")
            or tool_result.output
            or "Simulation completed."
        )
        return {
            "answer": answer,
            "completion": None,
            "tool": "general_simulation",
            "simulation": {
                "scenario_id": simulation.get("scenario_id", resolved),
                "question": simulation.get("question", latest),
                "affected_entities": simulation.get("affected_entities", []),
                "solver": simulation.get("solver", {}),
                "tool_call_trace": simulation.get("tool_call_trace", []),
                "success": True,
            },
        }

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
        # Broad catch: best-effort RAG retrieval (langchain/DB) may raise varied errors; degrade to no context.
        except Exception as exc:
            logger.warning("Vector store retrieval failed: %s", exc)
            return ""

    def list_vector_stores(self) -> list[dict[str, Any]]:
        """Expose LlamaStack vector stores for the chat UI."""
        return self.llama_stack_client.list_vector_stores()
