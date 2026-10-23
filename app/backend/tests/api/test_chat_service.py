"""Tests for ``ChatService`` guardrails, RAG, and LLM tool calling."""

from unittest.mock import MagicMock

import pytest
from services.agent_service import ToolResult
from services.chat_service import ChatService
from services.guardrail_policy import GUARDRAIL_RESPONSE


@pytest.fixture
def chat_service(mock_llama_stack_client):
    return ChatService(mock_llama_stack_client)


def test_guardrail_blocks_off_topic(chat_service):
    out = chat_service.reply("Do you know a good pizza place?", chat_history=[])
    assert out["answer"] == GUARDRAIL_RESPONSE
    mock_llama = chat_service.llama_stack_client
    mock_llama.ask_with_tools.assert_not_called()


def test_reply_uses_llama_with_context_from_vector_store_id(
    chat_service, mock_llama_stack_client
):
    out = chat_service.reply(
        "Summarize supplier risk",
        chat_history=[],
        vector_store_id="vs_abc",
    )
    assert out["answer"] == "mocked answer"
    mock_llama_stack_client.search_vector_store.assert_called_once_with(
        "vs_abc", "Summarize supplier risk", max_num_results=8
    )
    mock_llama_stack_client.ask_with_tools.assert_called_once()
    call_kw = mock_llama_stack_client.ask_with_tools.call_args.kwargs
    assert call_kw["context"] == "context chunk"
    assert call_kw["tools"] is not None
    assert callable(call_kw["execute_tool"])


def test_latest_user_text_prefers_history():
    mock_llama = MagicMock()
    mock_llama.ask_with_tools.return_value = {
        "answer": "ok",
        "completion": None,
        "tool_calls_made": [],
    }
    agent = MagicMock()
    agent.openai_tools.return_value = []
    svc = ChatService(mock_llama, agent_service=agent)
    history = [
        {"role": "human", "content": "first"},
        {"role": "ai", "content": "mid"},
        {"role": "human", "content": "  latest question  "},
    ]
    svc.reply("ignored fallback", chat_history=history)
    mock_llama.ask_with_tools.assert_called_once()
    assert mock_llama.ask_with_tools.call_args.args[0] == "latest question"


def test_map_chat_history_roles():
    history = [
        {"role": "human", "content": "hi"},
        {"role": "ai", "content": "hello"},
        {"role": "system", "content": "skip"},
        {"role": "human", "content": ""},
    ]
    mapped = ChatService._map_chat_history(history)
    assert mapped == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]



def test_reply_stream_guardrail(chat_service):
    events = list(chat_service.reply_stream("best pizza in town", chat_history=[]))
    assert events == [
        {"type": "done", "answer": GUARDRAIL_RESPONSE, "completion": None},
    ]
    chat_service.llama_stack_client.ask_stream_with_tools.assert_not_called()


def test_reply_stream_delegates_to_llama(chat_service, mock_llama_stack_client):
    events = list(chat_service.reply_stream("Summarize supplier risk", chat_history=[]))
    assert [e["type"] for e in events] == ["delta", "delta", "done"]
    assert events[-1]["answer"] == "mocked answer"
    mock_llama_stack_client.ask_stream_with_tools.assert_called_once()


def test_llm_tool_calling_binds_vector_store_for_knowledge_base(mock_llama_stack_client):
    agent = MagicMock()
    agent.openai_tools.return_value = []
    agent.run_tool.return_value = ToolResult(
        success=True,
        output="KB hit",
        data="KB hit",
    )

    def _ask_with_tools(*_args, execute_tool=None, **_kwargs):
        msg = execute_tool("knowledge_base", {"query": "supplier risk"})
        assert msg == "KB hit"
        return {"answer": "Based on docs…", "completion": None, "tool_calls_made": []}

    mock_llama_stack_client.ask_with_tools.side_effect = _ask_with_tools
    svc = ChatService(
        mock_llama_stack_client,
        agent_service=agent,
    )
    out = svc.reply("supplier risk?", chat_history=[], vector_store_id="vs_abc")
    assert out["tool"] == "knowledge_base"
    agent.run_tool.assert_called_once_with(
        "knowledge_base",
        query="supplier risk",
        vector_store_id="vs_abc",
    )


def test_llm_tool_calling_fetch_news(mock_llama_stack_client):
    agent = MagicMock()
    agent.openai_tools.return_value = []
    agent.run_tool.return_value = ToolResult(
        success=True,
        output="Headlines…",
        data=[{"title": "Port strike", "source": "BBC"}],
    )

    def _ask_with_tools(*_args, execute_tool=None, **_kwargs):
        execute_tool("fetch_news", {"limit": 12})
        return {"answer": "Headlines…", "completion": None, "tool_calls_made": []}

    mock_llama_stack_client.ask_with_tools.side_effect = _ask_with_tools
    svc = ChatService(
        mock_llama_stack_client,
        agent_service=agent,
    )
    out = svc.reply("Any supply chain news?", chat_history=[])
    assert out["tool"] == "fetch_news"
    assert out["news"][0]["title"] == "Port strike"


def test_news_knowledge_base_tool_is_always_available():
    """Asking about news must surface the news_knowledge_base tool on every run."""
    from services.agent_service import AgentService

    agent = AgentService(MagicMock())
    tool_names = {t["function"]["name"] for t in agent.openai_tools()}
    assert "news_knowledge_base" in tool_names


def test_llm_tool_calling_news_knowledge_base(mock_llama_stack_client):
    agent = MagicMock()
    agent.openai_tools.return_value = []
    agent.run_tool.return_value = ToolResult(
        success=True,
        output="Article: Port of Rotterdam tightens due to port congestion.",
        data="Article: Port of Rotterdam tightens due to port congestion.",
    )

    def _ask_with_tools(*_args, execute_tool=None, **_kwargs):
        msg = execute_tool("news_knowledge_base", {"query": "latest port congestion news"})
        assert "Port of Rotterdam" in msg
        return {
            "answer": "Here is the latest port news.",
            "completion": None,
            "tool_calls_made": [],
        }

    mock_llama_stack_client.ask_with_tools.side_effect = _ask_with_tools
    svc = ChatService(
        mock_llama_stack_client,
        agent_service=agent,
    )
    out = svc.reply("What is the latest news about port congestion?", chat_history=[])
    assert out["tool"] == "news_knowledge_base"
    agent.run_tool.assert_called_once_with(
        "news_knowledge_base",
        query="latest port congestion news",
    )


def test_news_knowledge_base_tool_runs_when_user_asks_about_news(mock_llama_stack_client):
    """End-to-end: LLM selects news_knowledge_base; search hits the news vector store."""
    from services.agent_service import AgentService

    news_store = MagicMock()
    news_store.search.return_value = "Article: Supply chain disruptions in Southeast Asia."
    news_store.vector_store_id = "vs_news"

    client = mock_llama_stack_client
    client.ask_with_tools.side_effect = []
    agent = AgentService(
        client,
        news_vector_store=news_store,
    )

    def _ask_with_tools(*_args, execute_tool=None, **_kwargs):
        result = execute_tool("news_knowledge_base", {"query": "supply chain disruption news"})
        assert "Supply chain disruptions" in result
        return {
            "answer": "Recent article: supply chain disruptions in Southeast Asia.",
            "completion": None,
            "tool_calls_made": [{"name": "news_knowledge_base"}],
        }

    client.ask_with_tools.side_effect = _ask_with_tools
    svc = ChatService(client, agent_service=agent)
    out = svc.reply("Any news on supply chain disruptions?", chat_history=[])
    assert out["tool"] == "news_knowledge_base"
    news_store.search.assert_called_once_with(
        "supply chain disruption news",
        max_results=5,
    )


def test_retrieve_context_merges_news_vector_store(mock_llama_stack_client):
    """News vector store hits are merged into LLM context alongside KB context."""
    news_store = MagicMock()
    news_store.search.return_value = "News: Suez canal traffic delayed by storm."
    svc = ChatService(
        mock_llama_stack_client,
        news_vector_store=news_store,
    )
    ctx = svc._retrieve_context("what is happening at the suez canal?")
    assert "News: Suez canal traffic delayed by storm." in ctx

    news_store.search.assert_called_once_with(
        "what is happening at the suez canal?",
        max_results=3,
    )


def test_reply_keeps_context_when_history_is_empty(mock_llama_stack_client):
    """Cleared chat (empty history) still retrieves KB context."""
    svc = ChatService(mock_llama_stack_client)
    svc.reply(
        "Show me the affected routes",
        chat_history=[],
        scenario_id="opensky-uk-closure-001",
        vector_store_id="vs_newsroom",
    )
    # Context should still be retrieved from vector store with empty history
    mock_llama_stack_client.search_vector_store.assert_called_once_with(
        "vs_newsroom",
        "Show me the affected routes",
        max_num_results=8,
    )
    # The LLM call should happen with context but empty conversation
    call_kw = mock_llama_stack_client.ask_with_tools.call_args.kwargs
    assert call_kw["context"] == "context chunk"
    assert call_kw["conversation_messages"] == []


def test_reply_keeps_scenario_context_when_history_is_empty(mock_llama_stack_client):
    """Scenario ID is still injected into the LLM prompt with cleared history."""
    svc = ChatService(mock_llama_stack_client)
    svc.reply(
        "What-if impact?",
        chat_history=[],  # cleared history
        scenario_id="opensky-uk-closure-001",
    )
    call_kw = mock_llama_stack_client.ask_with_tools.call_args.kwargs
    ctx = call_kw["scenario_context"]
    assert "Active simulation scenario: opensky-uk-closure-001 (UK Airspace Closure)." in ctx
    assert "NATS GPS failure" in ctx
    assert call_kw["conversation_messages"] == []


def test_map_chat_history_returns_empty_for_cleared_session():
    """After clearing, mapped history is empty."""
    mapped = ChatService._map_chat_history([])
    assert mapped == []


def test_reply_with_history_retrieves_context(mock_llama_stack_client):
    """Context is retrieved from vector store when history is non-empty."""
    svc = ChatService(mock_llama_stack_client)
    history = [
        {"role": "human", "content": "previous question"},
        {"role": "ai", "content": "previous answer"},
        {"role": "human", "content": "follow-up"},
    ]
    svc.reply(
        "follow-up",
        chat_history=history,
        vector_store_id="vs_kb",
    )
    # Context query uses the text content
    mock_llama_stack_client.search_vector_store.assert_called_once()
    call_args = mock_llama_stack_client.search_vector_store.call_args
    assert call_args[0][0] == "vs_kb"
    # conversation_messages should contain the mapped history
    call_kw = mock_llama_stack_client.ask_with_tools.call_args.kwargs
    assert len(call_kw["conversation_messages"]) == 3


def test_reply_injects_active_scenario_context(mock_llama_stack_client):
    """The active scenario is named in the LLM context block (not only the tool)."""
    svc = ChatService(mock_llama_stack_client)
    svc.reply(
        "What is the impact?",
        chat_history=[],
        scenario_id="opensky-uk-closure-001",
        vector_store_id="vs_abc",
    )
    call_kw = mock_llama_stack_client.ask_with_tools.call_args.kwargs
    ctx = call_kw["scenario_context"]
    assert "Active simulation scenario: opensky-uk-closure-001 (UK Airspace Closure)." in ctx
    assert "Scenario context:" in ctx
    assert call_kw["context"] == "context chunk"  # RAG context still retrieved


def test_reply_injects_latest_impact_result(mock_llama_stack_client):
    """Latest Impact Query payload is appended to the simulation context block."""
    svc = ChatService(mock_llama_stack_client)
    svc.reply(
        "Summarize the impact",
        chat_history=[],
        scenario_id="opensky-uk-closure-001",
        impact_result={
            "scenario_id": "opensky-uk-closure-001",
            "question": "Which flights are affected?",
            "answer": "Three aircraft are affected.",
            "affected_entities": ["opensky-1", "opensky-2"],
            "solver": {
                "impact_score": 0.5,
                "total_value_at_risk": 1000,
                "currency": "USD",
                "value_breakdown": [
                    {"entity_id": "opensky-2", "value_usd": 200},
                    {"entity_id": "opensky-1", "value_usd": 800, "callsign": "BAW442"},
                ],
            },
        },
    )
    ctx = mock_llama_stack_client.ask_with_tools.call_args.kwargs["scenario_context"]
    assert "Latest Impact Query result" in ctx
    assert "Three aircraft are affected." in ctx
    assert "opensky-1" in ctx
    assert "impact_score: 0.5" in ctx
    assert "opensky-1 [flight] (callsign=BAW442): 800 USD" in ctx
    assert "Do not redirect the user to Impact Query" in ctx
    assert "No Impact Query snapshot is loaded yet" not in ctx


def test_system_prompt_answers_from_loaded_impact_snapshot():
    from clients.chat_completion_client import SYSTEM_PROMPT

    assert "Latest Impact Query result" in SYSTEM_PROMPT
    assert "value_breakdown" in SYSTEM_PROMPT
    assert "inventing simulation results" not in SYSTEM_PROMPT
    assert "rather than inventing" not in SYSTEM_PROMPT


def test_reply_infers_scenario_context_from_user_text(mock_llama_stack_client):
    """When UI omits scenario_id, seeded clues still inject simulation context."""
    svc = ChatService(mock_llama_stack_client)
    svc.reply("What is the UK airspace impact?", chat_history=[], scenario_id="")
    ctx = mock_llama_stack_client.ask_with_tools.call_args.kwargs["scenario_context"]
    assert "opensky-uk-closure-001" in ctx
    assert "NATS GPS failure" in ctx


def test_reply_leaves_scenario_context_empty_without_scenario(mock_llama_stack_client):
    """Without an active scenario or clue, no scenario context block is sent."""
    svc = ChatService(mock_llama_stack_client)
    svc.reply("What is the impact?", chat_history=[], scenario_id="")
    call_kw = mock_llama_stack_client.ask_with_tools.call_args.kwargs
    assert call_kw["scenario_context"] == ""


def test_reply_stream_injects_active_scenario_context(mock_llama_stack_client):
    svc = ChatService(mock_llama_stack_client)
    list(svc.reply_stream("What is the impact?", chat_history=[], scenario_id="opensky-uk-closure-001"))
    call_kw = mock_llama_stack_client.ask_stream_with_tools.call_args.kwargs
    ctx = call_kw["scenario_context"]
    assert "Active simulation scenario: opensky-uk-closure-001 (UK Airspace Closure)." in ctx


def test_scenario_context_block_absent_without_scenario():
    from clients.chat_completion_client import LlamaStackChatClient
    from services.simulation_intent import scenario_context_block

    messages = LlamaStackChatClient(base_url="http://unused:1", label="test").build_messages(
        "hi",
        context="kb chunk",
        conversation_messages=[],
        scenario_context=scenario_context_block(""),
    )
    system = messages[0]["content"]
    assert "Active simulation scenario" not in system
    assert "Relevant context from the knowledge base" in system


def test_scenario_context_block_prepends_scenario_before_kb_context():
    from clients.chat_completion_client import LlamaStackChatClient
    from services.simulation_intent import scenario_context_block

    messages = LlamaStackChatClient(base_url="http://unused:1", label="test").build_messages(
        "hi",
        context="kb chunk",
        conversation_messages=[],
        scenario_context=scenario_context_block("supply-chain-port-strike-la"),
    )
    system = messages[0]["content"]
    assert "Active simulation scenario: supply-chain-port-strike-la (Port Strike LA)." in system
    assert "Scenario context:" in system
    assert "Relevant context from the knowledge base" in system
    assert system.index("Active simulation scenario") < system.index("Relevant context")


def test_system_prompt_lists_all_registered_tools(mock_llama_stack_client):
    """Every tool the agent exposes must be named in the static system prompt."""
    from clients.chat_completion_client import SYSTEM_PROMPT
    from services.agent_service import AgentService

    agent = AgentService(mock_llama_stack_client)
    registered = {t["function"]["name"] for t in agent.openai_tools()}
    assert registered == {
        "news_knowledge_base",
        "knowledge_base",
        "fetch_news",
    }
    assert "general_simulation" not in registered
    assert "general_simulation" not in SYSTEM_PROMPT
    for name in registered:
        assert name in SYSTEM_PROMPT, f"{name!r} must be named in SYSTEM_PROMPT"
