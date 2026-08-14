import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Optional

from clients.llama_stack_client import LlamaStackClient
from clients.vector_store_client import VectorStoreClient
from services.agent_service import AgentService, ToolResult
from services.guardrail_policy import GuardrailPolicy
from services.news_vector_store_service import NewsVectorStoreService
from services.rag_context_provider import RagContextProvider
from services.simulation_intent import normalize_scenario_id

logger = logging.getLogger(__name__)

_TOOL_PRIORITY = ("general_simulation", "fetch_news", "knowledge_base")


@dataclass(frozen=True)
class _PreparedChatTurn:
    """Normalized inputs shared by sync and streaming reply paths."""

    latest: str
    client: LlamaStackClient
    context: str
    conversation: list[dict[str, str]]


@dataclass
class _ToolSideEffects:
    """Collect UI payloads while tools run inside the LLM loop."""

    names: list[str] = field(default_factory=list)
    simulation: Optional[dict[str, Any]] = None
    news: Optional[list[Any]] = None
    latest_user: str = ""
    vector_store_id: str = ""
    scenario_id: str = ""
    agent_service: Optional[AgentService] = None

    def execute(self, name: str, args: dict[str, Any]) -> str:
        assert self.agent_service is not None
        bound = dict(args or {})
        if name == "knowledge_base":
            if not (bound.get("vector_store_id") or "").strip() and self.vector_store_id:
                bound["vector_store_id"] = self.vector_store_id
            if not (bound.get("query") or "").strip():
                bound["query"] = self.latest_user
            if not (bound.get("vector_store_id") or "").strip():
                return (
                    "Error: no knowledge base is selected. "
                    "Choose a scenario with a matched knowledge base, or pass vector_store_id."
                )
        elif name == "general_simulation":
            question = (bound.get("question") or "").strip() or self.latest_user
            bound["question"] = question
            bound["scenario_id"] = normalize_scenario_id(
                bound.get("scenario_id") or "",
                active_scenario_id=self.scenario_id,
                question=question,
            )
            if not (bound.get("scenario_id") or "").strip():
                return (
                    "Error: no active scenario. Select a scenario in Impact Query "
                    "(UK Airspace Closure, Port Strike LA, or Suez Blockage), "
                    "or pass scenario_id."
                )

        logger.info("ChatService: LLM requested tool %s args_keys=%s", name, list(bound.keys()))
        result = self.agent_service.run_tool(name, **bound)
        self.names.append(name)
        self._record_side_effects(name, bound, result)
        if result.success:
            return result.output or "Tool completed successfully."
        return f"Error: {result.error or 'tool failed'}"

    def _record_side_effects(self, name: str, bound: dict[str, Any], result: ToolResult) -> None:
        if not result.success:
            return
        if name == "general_simulation" and isinstance(result.data, dict):
            simulation = result.data
            self.simulation = {
                "scenario_id": simulation.get("scenario_id", bound.get("scenario_id", "")),
                "question": simulation.get("question", bound.get("question", self.latest_user)),
                "affected_entities": simulation.get("affected_entities", []),
                "solver": simulation.get("solver", {}),
                "tool_call_trace": simulation.get("tool_call_trace", []),
                "success": True,
                "answer": simulation.get("answer") or result.output,
            }
        elif name == "fetch_news" and isinstance(result.data, list):
            self.news = result.data


class ChatService:
    def __init__(
        self,
        llama_stack_client: LlamaStackClient,
        vector_store_client: Optional[VectorStoreClient] = None,
        openai_client: Optional[LlamaStackClient] = None,
        agent_service: Optional[AgentService] = None,
        news_vector_store: Optional[NewsVectorStoreService] = None,
    ):
        self.llama_stack_client = llama_stack_client
        self.openai_client: LlamaStackClient = openai_client or llama_stack_client
        self.vector_store_client = vector_store_client
        self.agent_service = agent_service or AgentService(llama_stack_client)
        self.news_vector_store = news_vector_store
        self._guardrails = GuardrailPolicy()
        self._rag = RagContextProvider(llama_stack_client, vector_store_client)

    def reply(
        self,
        user_input: str,
        chat_history: Optional[list[dict[str, Any]]] = None,
        vector_store_id: Optional[str] = None,
        use_vllm: bool = True,
        scenario_id: Optional[str] = None,
    ) -> dict:
        shortcut = self._early_reply(user_input, chat_history)
        if shortcut is not None:
            return shortcut

        turn = self._prepare_llm_turn(user_input, chat_history, vector_store_id, use_vllm)
        self._log_llm_routing(turn.client, use_vllm, streaming=False)
        tracker = self._new_tool_tracker(turn.latest, vector_store_id, scenario_id)
        llm_result = turn.client.ask_with_tools(
            turn.latest,
            context=turn.context,
            conversation_messages=turn.conversation,
            tools=self.agent_service.openai_tools(),
            execute_tool=tracker.execute,
        )
        answer = llm_result.get("answer", "")
        logger.info(
            "ChatService: answer received from LlamaStack[%s] model=%s tools=%s",
            turn.client.label,
            turn.client.model,
            tracker.names,
        )
        return self._attach_tool_payload(
            {
                "answer": answer,
                "completion": llm_result.get("completion"),
            },
            tracker,
        )

    def reply_stream(
        self,
        user_input: str,
        chat_history: Optional[list[dict[str, Any]]] = None,
        vector_store_id: Optional[str] = None,
        use_vllm: bool = True,
        scenario_id: Optional[str] = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield SSE-friendly chat events (guardrails, route shortcuts, or LLM+tools stream)."""
        shortcut = self._early_reply(user_input, chat_history)
        if shortcut is not None:
            yield {"type": "done", **shortcut}
            return

        turn = self._prepare_llm_turn(user_input, chat_history, vector_store_id, use_vllm)
        self._log_llm_routing(turn.client, use_vllm, streaming=True)
        tracker = self._new_tool_tracker(turn.latest, vector_store_id, scenario_id)
        for event in turn.client.ask_stream_with_tools(
            turn.latest,
            context=turn.context,
            conversation_messages=turn.conversation,
            tools=self.agent_service.openai_tools(),
            execute_tool=tracker.execute,
        ):
            if event.get("type") == "done":
                yield self._attach_tool_payload({**event}, tracker)
            else:
                yield event

    def _new_tool_tracker(
        self,
        latest: str,
        vector_store_id: Optional[str],
        scenario_id: Optional[str],
    ) -> _ToolSideEffects:
        return _ToolSideEffects(
            latest_user=latest,
            vector_store_id=(vector_store_id or "").strip(),
            scenario_id=(scenario_id or "").strip(),
            agent_service=self.agent_service,
        )

    @staticmethod
    def _primary_tool_name(names: list[str]) -> Optional[str]:
        if not names:
            return None
        for preferred in _TOOL_PRIORITY:
            if preferred in names:
                return preferred
        return names[-1]

    def _attach_tool_payload(
        self,
        payload: dict[str, Any],
        tracker: _ToolSideEffects,
    ) -> dict[str, Any]:
        primary = self._primary_tool_name(tracker.names)
        if primary:
            payload["tool"] = primary
        if tracker.simulation is not None:
            payload["simulation"] = tracker.simulation
        if tracker.news is not None:
            payload["news"] = tracker.news
        return payload

    def _early_reply(
        self,
        user_input: str,
        chat_history: Optional[list[dict[str, Any]]],
    ) -> Optional[dict[str, Any]]:
        """Return a guardrail response, or ``None`` to call the LLM with tools."""
        history = chat_history if isinstance(chat_history, list) else []
        latest = self._latest_user_text(history, user_input)

        if self._guardrails.is_blocked(latest):
            return self._guardrails.blocked_response()

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
        base_context = self._rag.get_context(query, vector_store_id=vector_store_id)
        news_context = ""
        if self.news_vector_store:
            try:
                news_context = self.news_vector_store.search(query, max_results=3)
            except Exception:
                logger.warning("ChatService: news vector store search failed", exc_info=True)
        if base_context and news_context:
            return base_context + "\n\n[Recent News Context]\n\n" + news_context
        return base_context + news_context

    def list_vector_stores(self) -> list[dict[str, Any]]:
        """Expose LlamaStack vector stores for the chat UI."""
        return self.llama_stack_client.list_vector_stores()
