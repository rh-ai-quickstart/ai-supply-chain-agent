import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from clients.general_simulation_client import GeneralSimulationClient
from clients.llama_stack_client import LlamaStackClient
from services.general_simulation_service import GeneralSimulationService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    fn: Callable[..., Any]


@dataclass
class ToolResult:
    success: bool
    output: str
    data: Any = None
    error: Optional[str] = None


def _default_kb_params() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query for the knowledge base",
            },
            "vector_store_id": {
                "type": "string",
                "description": "The vector store ID to search in",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default 5)",
                "default": 5,
            },
        },
        "required": ["query", "vector_store_id"],
    }


class AgentService:
    def __init__(
        self,
        llama_stack_client: LlamaStackClient,
        general_simulation_client: GeneralSimulationClient | None = None,
    ):
        self._llama_client = llama_stack_client
        self._sim_service = GeneralSimulationService(
            client=general_simulation_client or GeneralSimulationClient(),
        )
        self._tools: dict[str, ToolSpec] = {}
        self._register_tools()

    def _register_tools(self) -> None:
        knowledge_base = ToolSpec(
            name="knowledge_base",
            description="Search the knowledge base for relevant supply chain information",
            parameters=_default_kb_params(),
            fn=self._run_knowledge_base,
        )
        self._tools[knowledge_base.name] = knowledge_base

        general_simulation = ToolSpec(
            name="general_simulation",
            description="Run a what-if simulation scenario through the general-simulation impact-reasoning engine. Queries a Neo4j graph of supply chain dependencies, runs a quantitative solver, and returns a grounded LLM analysis of the impact.",
            parameters={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Natural-language question about the simulation scenario (e.g. 'Which flights are affected by the UK airspace closure?')",
                    },
                    "scenario_id": {
                        "type": "string",
                        "description": "ID of the simulation scenario to reason about (e.g. 'opensky-uk-closure-001')",
                    },
                },
                "required": ["question", "scenario_id"],
            },
            fn=self._run_general_simulation,
        )
        self._tools[general_simulation.name] = general_simulation

        unknown = ToolSpec(
            name="unknown",
            description="A placeholder tool for future functionality — not yet implemented",
            parameters={
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "description": "Arbitrary input for the placeholder tool",
                    },
                },
                "required": ["input"],
            },
            fn=self._run_unknown,
        )
        self._tools[unknown.name] = unknown

    @property
    def tools(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def run_tool(self, name: str, **kwargs: Any) -> ToolResult:
        tool = self.get_tool(name)
        if tool is None:
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown tool: {name}",
            )
        try:
            return tool.fn(**kwargs)
        except Exception as exc:
            logger.error("Tool %s failed: %s", name, exc)
            return ToolResult(
                success=False,
                output="",
                error=str(exc),
            )

    def _run_knowledge_base(
        self,
        query: str,
        vector_store_id: str,
        max_results: int = 5,
    ) -> ToolResult:
        if not query or not query.strip():
            return ToolResult(success=False, output="", error="query is required")
        if not vector_store_id:
            return ToolResult(success=False, output="", error="vector_store_id is required")

        context = self._llama_client.search_vector_store(
            vector_store_id,
            query.strip(),
            max_num_results=max_results,
        )
        if not context:
            return ToolResult(
                success=True,
                output="No relevant information found in the knowledge base.",
                data=[],
            )

        return ToolResult(
            success=True,
            output=context,
            data=context,
        )

    def _run_general_simulation(self, question: str, scenario_id: str) -> ToolResult:
        if not question or not question.strip():
            return ToolResult(success=False, output="", error="question is required")
        if not scenario_id or not scenario_id.strip():
            return ToolResult(success=False, output="", error="scenario_id is required")

        result = self._sim_service.run_simulation(question, scenario_id)
        if not result.get("success"):
            return ToolResult(
                success=False,
                output="",
                error=result.get("error", "simulation failed"),
            )

        answer = result.get("answer", "")
        entities = result.get("affected_entities", [])
        solver = result.get("solver", {})
        trace = result.get("tool_call_trace", [])

        summary = (
            f"Simulation result for scenario '{scenario_id}':\n\n"
            f"{answer}\n\n"
            f"Affected entities ({len(entities)}): {', '.join(entities) if entities else 'none'}\n"
            f"Impact score: {solver.get('impact_score', 'N/A')}\n"
            f"Value at risk: {solver.get('total_value_at_risk', 'N/A')} {solver.get('currency', 'USD')}\n"
            f"Tool calls made: {len(trace)}"
        )

        return ToolResult(
            success=True,
            output=summary,
            data=result,
        )

    def _run_unknown(self, input: str = "") -> ToolResult:
        return ToolResult(
            success=True,
            output=f"Placeholder tool 'unknown' received input: {input}. Not yet implemented.",
            data=input,
        )
