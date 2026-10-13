from dataclasses import dataclass
from typing import Any, Callable, Optional

from clients.llama_stack_client import LlamaStackClient
from clients.news_client import NewsClient
from services.news_service import NewsService
from services.news_vector_store_service import NewsVectorStoreService
from logging_config import getLogger

logger = getLogger(__name__)

# general_simulation is intentionally omitted: Impact Query owns that path;
# exposing it in general chat caused excessive / noisy tool calls.
_LLM_TOOL_NAMES = ("news_knowledge_base", "knowledge_base", "fetch_news")


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
                "description": (
                    "The vector store ID to search in. "
                    "Optional when the UI already selected a knowledge base."
                ),
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return (default 5)",
                "default": 5,
            },
        },
        "required": ["query"],
    }


class AgentService:
    def __init__(
        self,
        llama_stack_client: LlamaStackClient,
        news_client: NewsClient | None = None,
        news_vector_store: NewsVectorStoreService | None = None,
    ):
        self._llama_client = llama_stack_client
        self._news_service = NewsService(client=news_client or NewsClient())
        self._news_vector_store = news_vector_store
        self._tools: dict[str, ToolSpec] = {}
        self._register_tools()

    def _register_tools(self) -> None:
        news_knowledge_base = ToolSpec(
            name="news_knowledge_base",
            description=(
                "Search the recent news knowledge base for relevant, up-to-date news "
                "articles about supply chains, logistics, trade, and disruptions. "
                "Use for questions about the latest news, current events, or recent "
                "disruptions affecting the supply chain."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query for the news knowledge base",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
            fn=self._run_news_knowledge_base,
        )
        self._tools[news_knowledge_base.name] = news_knowledge_base

        knowledge_base = ToolSpec(
            name="knowledge_base",
            description=(
                "Search the knowledge base for relevant supply chain information "
                "from uploaded documents."
            ),
            parameters=_default_kb_params(),
            fn=self._run_knowledge_base,
        )
        self._tools[knowledge_base.name] = knowledge_base

        fetch_news = ToolSpec(
            name="fetch_news",
            description=(
                "Fetch the latest world and business news headlines from RSS feeds "
                "and summarize those most likely to affect supply chains."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum headlines to include (default 12)",
                        "default": 12,
                    },
                },
                "required": [],
            },
            fn=self._run_fetch_news,
        )
        self._tools[fetch_news.name] = fetch_news

    @property
    def tools(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def get_tool(self, name: str) -> Optional[ToolSpec]:
        return self._tools.get(name)

    def openai_tools(self) -> list[dict[str, Any]]:
        """OpenAI-compatible tool schemas for chat completions ``tools=``."""
        out: list[dict[str, Any]] = []
        for name in _LLM_TOOL_NAMES:
            tool = self._tools.get(name)
            if tool is None:
                continue
            out.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
            )
        return out

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
        # Broad catch: tool callables are arbitrary; surface any failure as a ToolResult error.
        except Exception as exc:
            logger.error("Tool %s failed: %s", name, exc)
            return ToolResult(
                success=False,
                output="",
                error=str(exc),
            )

    def _run_news_knowledge_base(
        self,
        query: str,
        max_results: int = 5,
    ) -> ToolResult:
        if not query or not query.strip():
            return ToolResult(success=False, output="", error="query is required")
        if self._news_vector_store is None:
            return ToolResult(
                success=False,
                output="",
                error="News knowledge base is not available",
            )

        context = self._news_vector_store.search(
            query.strip(),
            max_results=max_results,
        )
        if not context:
            return ToolResult(
                success=True,
                output="No recent news articles found matching that query.",
                data=[],
            )

        return ToolResult(
            success=True,
            output=context,
            data=context,
        )

    def _run_knowledge_base(
        self,
        query: str,
        vector_store_id: str = "",
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

    def _run_fetch_news(self, limit: int = 12) -> ToolResult:
        payload = self._news_service.get_headlines(limit=max(int(limit or 12), 12))
        items = payload.get("items") or []
        if not items:
            return ToolResult(
                success=False,
                output="",
                error="No news headlines available",
            )
        answer = self._news_service.format_for_chat(items, limit=limit)
        return ToolResult(
            success=True,
            output=answer,
            data=items,
        )
