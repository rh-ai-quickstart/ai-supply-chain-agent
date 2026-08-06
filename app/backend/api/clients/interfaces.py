"""Narrow ``Protocol`` seams for LlamaStack/OpenAI-compatible collaborators.

Splitting the client surface into small protocols lets each consumer depend
only on the capability it actually uses (Interface Segregation), and lets any
OpenAI-compatible backend be substituted without consumers caring about the
concrete class (Liskov substitution / Dependency Inversion).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ChatCompletionClient(Protocol):
    """Plain (non-tool-calling) chat completions."""

    label: str
    model: str
    base_url: str

    def ask(
        self,
        user_input: str,
        context: str = "",
        conversation_messages: list[dict] | None = None,
    ) -> dict[str, Any]: ...

    def ask_stream(
        self,
        user_input: str,
        context: str = "",
        conversation_messages: list[dict] | None = None,
    ) -> Iterator[dict[str, Any]]: ...


@runtime_checkable
class ToolCallingClient(Protocol):
    """Chat completions with an agentic tool-calling loop."""

    label: str
    model: str
    base_url: str

    def ask_with_tools(
        self,
        user_input: str,
        context: str = "",
        conversation_messages: list[dict] | None = None,
        tools: list[dict[str, Any]] | None = None,
        execute_tool: Callable[[str, dict[str, Any]], str] | None = None,
        max_rounds: int = 3,
    ) -> dict[str, Any]: ...

    def ask_stream_with_tools(
        self,
        user_input: str,
        context: str = "",
        conversation_messages: list[dict] | None = None,
        tools: list[dict[str, Any]] | None = None,
        execute_tool: Callable[[str, dict[str, Any]], str] | None = None,
        max_rounds: int = 3,
    ) -> Iterator[dict[str, Any]]: ...


@runtime_checkable
class VectorStoreAdminClient(Protocol):
    """Vector store administration (create/upload/attach/delete/search)."""

    def list_vector_stores(self, limit: int = 100) -> list[dict[str, Any]]: ...

    def search_vector_store(
        self,
        vector_store_id: str,
        query: str,
        *,
        max_num_results: int = 8,
    ) -> str: ...

    def create_vector_store(self, name: str) -> str: ...

    def upload_file_bytes(self, filename: str, content: bytes) -> str: ...

    def attach_file_to_vector_store(self, vector_store_id: str, file_id: str) -> None: ...

    def delete_vector_store(self, vector_store_id: str) -> None: ...
