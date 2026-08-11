"""Facade composing the split LlamaStack collaborators (SRP + composition).

``LlamaStackClient`` used to be a single 600+ line class doing three unrelated
jobs: plain chat completions, an agentic tool-calling loop, and vector-store
administration. Each job now lives in its own focused, independently-tested
class:

- ``clients.chat_completion_client.LlamaStackChatClient`` — connection setup,
  message building, plain ``ask``/``ask_stream``.
- ``clients.tool_loop_orchestrator.ToolLoopOrchestrator`` — the agentic
  tool-calling loop, composed with a chat client rather than inheriting from
  it.
- ``clients.llama_vector_store_admin.LlamaStackVectorStoreAdmin`` — vector
  store CRUD/search.

This class remains as a thin facade so existing call sites that need *all*
three capabilities through one object (``ChatService``, ``main``'s
knowledge-base upload route) don't need to juggle three separate references.
New/narrow consumers should prefer depending on the specific collaborator
they need (see ``Container`` in ``container.py``) rather than this facade.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

# Re-exported for backward compatibility with call sites/tests that imported
# these helpers from this module before the SRP split.
from clients.chat_completion_client import (
    DEFAULT_TIMEOUT_SECONDS,
    LlamaStackChatClient,
)
from clients.llama_vector_store_admin import LlamaStackVectorStoreAdmin
from clients.tool_loop_orchestrator import ToolLoopOrchestrator


def timeout_seconds_from_env(default: int = DEFAULT_TIMEOUT_SECONDS) -> int:
    """Read ``LLAMA_STACK_TIMEOUT_SECONDS`` (integer seconds)."""
    raw = os.getenv("LLAMA_STACK_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


class LlamaStackClient:
    """OpenAI-compatible client pointed at a Llama Stack server.

    Facade over ``LlamaStackChatClient`` + ``ToolLoopOrchestrator`` +
    ``LlamaStackVectorStoreAdmin``.
    """

    def __init__(
        self,
        timeout_seconds: int | None = None,
        base_url: str | None = None,
        model: str | None = None,
        label: str = "vllm",
        api_key: str | None = None,
        vector_store_provider: str | None = None,
    ):
        env_url = os.getenv("LLAMA_STACK_URL", "http://llamastack:8321")
        resolved_base_url = (base_url or env_url).rstrip("/")
        resolved_model = model or os.getenv(
            "LLAMA_STACK_MODEL",
            "llama-3-2-3b-instruct/meta-llama/Llama-3.2-3B-Instruct",
        )
        resolved_timeout = (
            timeout_seconds if timeout_seconds is not None else timeout_seconds_from_env()
        )

        self._chat = LlamaStackChatClient(
            base_url=resolved_base_url,
            model=resolved_model,
            label=label,
            timeout_seconds=resolved_timeout,
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
        )
        self._tools = ToolLoopOrchestrator(self._chat)
        self._vector_admin = LlamaStackVectorStoreAdmin(
            self._chat.client,
            vector_store_provider=(
                vector_store_provider or os.getenv("VECTOR_STORE_PROVIDER", "pgvector")
            ),
        )

    # -- identity / connection info (used for logging by ChatService) -----
    @property
    def base_url(self) -> str:
        return self._chat.base_url

    @property
    def model(self) -> str:
        return self._chat.model

    @property
    def label(self) -> str:
        return self._chat.label

    # -- backward-compatible internals (ScenarioCreateService's single-shot
    # "propose" completion reaches past the tool loop for a plain call) -----
    @property
    def _client(self):
        return self._chat.client

    def _completion_kwargs(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._chat.completion_kwargs(*args, **kwargs)

    @staticmethod
    def _completion_to_json(completion: Any) -> dict[str, Any]:
        return LlamaStackChatClient.completion_to_json(completion)

    # -- plain chat completions --------------------------------------------
    def ask(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._chat.ask(*args, **kwargs)

    def ask_stream(self, *args: Any, **kwargs: Any) -> Iterator[dict[str, Any]]:
        return self._chat.ask_stream(*args, **kwargs)

    # -- tool-calling loop ---------------------------------------------------
    def ask_with_tools(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self._tools.ask_with_tools(*args, **kwargs)

    def ask_stream_with_tools(self, *args: Any, **kwargs: Any) -> Iterator[dict[str, Any]]:
        return self._tools.ask_stream_with_tools(*args, **kwargs)

    # -- vector store administration ----------------------------------------
    def list_vector_stores(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return self._vector_admin.list_vector_stores(*args, **kwargs)

    def search_vector_store(self, *args: Any, **kwargs: Any) -> str:
        return self._vector_admin.search_vector_store(*args, **kwargs)

    def create_vector_store(self, *args: Any, **kwargs: Any) -> str:
        return self._vector_admin.create_vector_store(*args, **kwargs)

    def upload_file_bytes(self, *args: Any, **kwargs: Any) -> str:
        return self._vector_admin.upload_file_bytes(*args, **kwargs)

    def attach_file_to_vector_store(self, *args: Any, **kwargs: Any) -> None:
        return self._vector_admin.attach_file_to_vector_store(*args, **kwargs)

    def delete_vector_store(self, *args: Any, **kwargs: Any) -> None:
        return self._vector_admin.delete_vector_store(*args, **kwargs)
