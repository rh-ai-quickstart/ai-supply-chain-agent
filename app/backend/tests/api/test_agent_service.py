from unittest.mock import MagicMock

from services.agent_service import AgentService


def _make_mock_llama_stack() -> MagicMock:
    client = MagicMock()
    client.search_vector_store.return_value = "Found relevant supply chain data."
    return client


def _make_mock_sim_client() -> MagicMock:
    client = MagicMock()
    client.query.return_value = {
        "answer": "The UK airspace closure affects 12 cargo flights.",
        "scenario_id": "uk-closure-001",
        "question": "Which flights are affected?",
        "affected_entities": ["FLT001", "FLT002", "FLT003"],
        "solver": {
            "impact_score": 0.75,
            "total_value_at_risk": 4500000.0,
            "currency": "USD",
        },
        "tool_call_trace": [
            {"tool_name": "get_affected_subgraph", "arguments": {}, "output": {}}
        ],
    }
    return client


class TestAgentService:
    def test_tools_are_registered(self):
        service = AgentService(_make_mock_llama_stack())
        assert len(service.tools) == 4
        names = {t.name for t in service.tools}
        assert names == {
            "news_knowledge_base",
            "knowledge_base",
            "general_simulation",
            "fetch_news",
        }

    def test_openai_tools_matches_registered(self):
        service = AgentService(_make_mock_llama_stack())
        schemas = service.openai_tools()
        names = {s["function"]["name"] for s in schemas}
        assert names == {
            "news_knowledge_base",
            "knowledge_base",
            "general_simulation",
            "fetch_news",
        }
        assert all(s["type"] == "function" for s in schemas)

    def test_news_knowledge_base_tool_success(self):
        news_store = MagicMock()
        news_store.search.return_value = "Recent article about port congestion."
        service = AgentService(
            _make_mock_llama_stack(),
            news_vector_store=news_store,
        )
        result = service.run_tool(
            "news_knowledge_base",
            query="port congestion",
        )
        assert result.success is True
        assert result.output == "Recent article about port congestion."
        news_store.search.assert_called_once_with("port congestion", max_results=5)

    def test_news_knowledge_base_tool_empty_query(self):
        service = AgentService(_make_mock_llama_stack())
        result = service.run_tool("news_knowledge_base", query="   ")
        assert result.success is False
        assert "query" in result.error

    def test_news_knowledge_base_tool_no_results(self):
        news_store = MagicMock()
        news_store.search.return_value = ""
        service = AgentService(
            _make_mock_llama_stack(),
            news_vector_store=news_store,
        )
        result = service.run_tool(
            "news_knowledge_base",
            query="nothing relevant",
        )
        assert result.success is True
        assert "No recent news articles" in result.output

    def test_news_knowledge_base_tool_unavailable(self):
        service = AgentService(_make_mock_llama_stack())
        result = service.run_tool("news_knowledge_base", query="port congestion")
        assert result.success is False
        assert "News knowledge base is not available" in result.error

    def test_get_tool_returns_spec(self):
        service = AgentService(_make_mock_llama_stack())
        tool = service.get_tool("knowledge_base")
        assert tool is not None
        assert tool.name == "knowledge_base"
        assert "query" in tool.parameters["properties"]

    def test_get_tool_unknown_name_returns_none(self):
        service = AgentService(_make_mock_llama_stack())
        assert service.get_tool("nonexistent") is None

    def test_run_unknown_tool_returns_error(self):
        service = AgentService(_make_mock_llama_stack())
        result = service.run_tool("nonexistent")
        assert result.success is False
        assert "nonexistent" in result.error

    def test_knowledge_base_tool_success(self):
        client = _make_mock_llama_stack()
        service = AgentService(client)
        result = service.run_tool(
            "knowledge_base",
            query="supply chain risk",
            vector_store_id="vs_123",
        )
        assert result.success is True
        assert result.output == "Found relevant supply chain data."
        client.search_vector_store.assert_called_once_with(
            "vs_123", "supply chain risk", max_num_results=5,
        )

    def test_knowledge_base_tool_empty_query(self):
        service = AgentService(_make_mock_llama_stack())
        result = service.run_tool(
            "knowledge_base",
            query="   ",
            vector_store_id="vs_123",
        )
        assert result.success is False
        assert "query" in result.error

    def test_knowledge_base_tool_no_vector_store_id(self):
        service = AgentService(_make_mock_llama_stack())
        result = service.run_tool(
            "knowledge_base",
            query="risk",
            vector_store_id="",
        )
        assert result.success is False
        assert "vector_store_id" in result.error

    def test_knowledge_base_tool_no_results(self):
        client = _make_mock_llama_stack()
        client.search_vector_store.return_value = ""
        service = AgentService(client)
        result = service.run_tool(
            "knowledge_base",
            query="nothing relevant",
            vector_store_id="vs_empty",
        )
        assert result.success is True
        assert "No relevant information" in result.output

    def test_knowledge_base_tool_respects_max_results(self):
        client = _make_mock_llama_stack()
        service = AgentService(client)
        service.run_tool(
            "knowledge_base",
            query="risk",
            vector_store_id="vs_123",
            max_results=3,
        )
        client.search_vector_store.assert_called_once_with(
            "vs_123", "risk", max_num_results=3,
        )

    def test_tool_failure_is_caught(self):
        client = _make_mock_llama_stack()
        client.search_vector_store.side_effect = RuntimeError("search failed")
        service = AgentService(client)
        result = service.run_tool(
            "knowledge_base",
            query="risk",
            vector_store_id="vs_123",
        )
        assert result.success is False
        assert "search failed" in result.error

    def test_general_simulation_tool_success(self):
        sim_client = _make_mock_sim_client()
        service = AgentService(
            _make_mock_llama_stack(),
            general_simulation_client=sim_client,
        )
        result = service.run_tool(
            "general_simulation",
            question="Which flights are affected by the UK airspace closure?",
            scenario_id="uk-closure-001",
        )
        assert result.success is True
        assert "FLT001" in result.output
        assert "0.75" in result.output
        sim_client.query.assert_called_once_with(
            "Which flights are affected by the UK airspace closure?",
            "uk-closure-001",
        )

    def test_general_simulation_tool_empty_question(self):
        service = AgentService(
            _make_mock_llama_stack(),
            general_simulation_client=_make_mock_sim_client(),
        )
        result = service.run_tool(
            "general_simulation",
            question="   ",
            scenario_id="uk-closure-001",
        )
        assert result.success is False
        assert "question" in result.error

    def test_general_simulation_tool_empty_scenario_id(self):
        service = AgentService(
            _make_mock_llama_stack(),
            general_simulation_client=_make_mock_sim_client(),
        )
        result = service.run_tool(
            "general_simulation",
            question="Which flights are affected?",
            scenario_id="",
        )
        assert result.success is False
        assert "scenario_id" in result.error

    def test_general_simulation_tool_propagates_error(self):
        sim_client = _make_mock_sim_client()
        sim_client.query.return_value = {"error": "Service unavailable"}
        service = AgentService(
            _make_mock_llama_stack(),
            general_simulation_client=sim_client,
        )
        result = service.run_tool(
            "general_simulation",
            question="Which flights?",
            scenario_id="uk-closure-001",
        )
        assert result.success is False
        assert "Service unavailable" in result.error

    def test_general_simulation_tool_no_entities(self):
        sim_client = _make_mock_sim_client()
        sim_client.query.return_value = {
            "answer": "No entities affected.",
            "scenario_id": "empty-001",
            "question": "Is anything affected?",
            "affected_entities": [],
            "solver": {},
            "tool_call_trace": [],
        }
        service = AgentService(
            _make_mock_llama_stack(),
            general_simulation_client=sim_client,
        )
        result = service.run_tool(
            "general_simulation",
            question="Is anything affected?",
            scenario_id="empty-001",
        )
        assert result.success is True
        assert "none" in result.output

    def test_general_simulation_tool_spec_params(self):
        service = AgentService(_make_mock_llama_stack())
        tool = service.get_tool("general_simulation")
        assert tool is not None
        assert "question" in tool.parameters["properties"]
        assert "scenario_id" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["question"]

    def test_fetch_news_tool_success(self):
        news_client = MagicMock()
        news_client.fetch_headlines.return_value = [
            {
                "title": "Port strike disrupts shipping",
                "link": "https://example.com/1",
                "source": "BBC",
                "summary": "Dockworkers walk out",
                "published_at": "2026-08-05T12:00:00+00:00",
            }
        ]
        news_client.cache_age_seconds.return_value = 0.1
        service = AgentService(_make_mock_llama_stack(), news_client=news_client)
        result = service.run_tool("fetch_news", limit=12)
        assert result.success is True
        assert "Port strike" in result.output
        assert isinstance(result.data, list)
