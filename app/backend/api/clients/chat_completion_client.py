"""Plain (non-tool-calling) chat completions against an OpenAI-compatible endpoint.

Split out of the former monolithic ``LlamaStackClient`` (SRP): this class owns
only connection setup, message building, and plain ``ask``/``ask_stream``.
Tool-calling orchestration lives in ``tool_loop_orchestrator.py``, and vector
store administration lives in ``llama_vector_store_admin.py``.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from logging_config import getLogger
from openai import APIError, OpenAI
from tenacity import (
    retry,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an AI assistant for a supply chain command center. "
    "You help operators understand logistics data, demand forecasting, "
    "inventory levels, supplier risk, and shipping routes. "
    "Answer concisely and only about supply chain topics. "
    "If asked about unrelated topics, politely redirect to supply chain matters. "
    "You have tools: "
    "general_simulation (what-if / impact analysis for an active scenario), "
    "knowledge_base (search uploaded documents from the selected knowledge base), "
    "news_knowledge_base (search recent news articles about supply chains and disruptions), "
    "and fetch_news (latest world/business headlines that may affect logistics). "
    "Call a tool when it will improve your answer; otherwise reply directly."
)

NO_ENDPOINT_ANSWER = "Something went wrong. There is no endpoint configured."
EMPTY_COMPLETION_ANSWER = "Darn! Something went wrong."
CHAT_TEMPERATURE = 0.1

# Default matches frontend nginx proxy_read_timeout (300s) for slow CPU/GPU inference.
DEFAULT_TIMEOUT_SECONDS = 300

# Retry transient upstream failures a few times before giving up; a single
# slow token shouldn't fail a whole chat turn.
_RETRY_ATTEMPTS = 3
_RETRY_MIN_WAIT_SECONDS = 1
_RETRY_MAX_WAIT_SECONDS = 8


def _retryable_api_error(exc: BaseException) -> bool:
    """Retry on 5xx/429/connection-ish errors; not on 4xx client errors."""
    status = getattr(exc, "status_code", None)
    if status is None:
        return True
    return status >= 500 or status == 429


@dataclass
class _StreamAccumulator:
    """Collect streamed token text and completion metadata from OpenAI chunks."""

    parts: list[str] = field(default_factory=list)
    completion: dict[str, Any] = field(default_factory=dict)

    def absorb_chunk(self, chunk: Any, completion_to_json) -> str | None:
        """Merge one stream chunk; return delta text when present."""
        if chunk.usage is not None:
            usage = completion_to_json(chunk.usage)
            if usage:
                self.completion["usage"] = usage
        if chunk.model:
            self.completion["model"] = chunk.model
        if not chunk.choices:
            return None

        choice = chunk.choices[0]
        delta = choice.delta.content if choice.delta else None
        if delta:
            self.parts.append(delta)
        if choice.finish_reason:
            self.completion["finish_reason"] = choice.finish_reason
        return delta

    @property
    def answer(self) -> str:
        return "".join(self.parts) or EMPTY_COMPLETION_ANSWER


class LlamaStackChatClient:
    """OpenAI-compatible chat-completion client pointed at a Llama Stack server."""

    def __init__(
        self,
        *,
        base_url: str = "http://llamastack:8321",
        model: str = "llama-3-2-3b-instruct/meta-llama/Llama-3.2-3B-Instruct",
        label: str = "vllm",
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        api_key: str | None = None,
    ):
        self.base_url = base_url.rstrip("/") + "/v1"
        self.label = label
        self.model = model
        self._timeout = timeout_seconds

        # Local Llama Stack ignores the key; OpenAI (and other hosted APIs) require
        # a real one via the injected api_key.
        self.client = OpenAI(
            api_key=api_key or "not-required",
            base_url=self.base_url,
            timeout=self._timeout,
        )
        logger.info(
            "LlamaStackChatClient[%s]: base_url=%s model=%s timeout=%ss",
            self.label,
            self.base_url,
            self.model,
            self._timeout,
        )

    def build_messages(
        self,
        user_input: str,
        context: str = "",
        conversation_messages: list[dict] | None = None,
        scenario_context: str = "",
    ) -> list[dict]:
        # LiteMaaS / Qwen require a single system message at the start.
        # A second role=system (e.g. RAG context) triggers:
        # "System message must be at the beginning."
        system_parts = [SYSTEM_PROMPT]
        if scenario_context and str(scenario_context).strip():
            system_parts.append(str(scenario_context).strip())
        if context and str(context).strip():
            system_parts.append(
                f"Relevant context from the knowledge base:\n{str(context).strip()}"
            )
        messages: list[dict] = [
            {"role": "system", "content": "\n\n".join(system_parts)}
        ]

        turns = conversation_messages if conversation_messages else []
        if turns:
            messages.extend(self._sanitize_conversation_turns(turns))
        else:
            messages.append({"role": "user", "content": user_input})

        return messages

    @staticmethod
    def _sanitize_conversation_turns(turns: list[dict]) -> list[dict]:
        """Keep only chat turns that are valid after a leading system message."""
        allowed = {"user", "assistant", "tool"}
        out: list[dict] = []
        for turn in turns:
            role = (turn.get("role") or "").strip()
            if role not in allowed:
                continue
            out.append(turn)
        return out

    @staticmethod
    def completion_to_json(completion: Any) -> dict[str, Any]:
        """Serialize an OpenAI ``ChatCompletion`` (or similar) for API responses."""
        if completion is None:
            return {}
        try:
            dumped = completion.model_dump(mode="json")
            return dumped if isinstance(dumped, dict) else {"value": dumped}
        except (ValueError, TypeError, AttributeError) as exc:
            logger.warning("LlamaStackChatClient: could not model_dump completion: %s", exc)
            return {"serialization_error": str(exc)}

    def log_chat_request(self, *, streaming: bool, message_count: int) -> None:
        mode = "streaming" if streaming else "sending"
        logger.info(
            "LlamaStackChatClient[%s]: %s request — base_url=%s model=%s message_count=%d",
            self.label,
            mode,
            self.base_url,
            self.model,
            message_count,
        )

    def completion_kwargs(
        self,
        messages: list[dict],
        *,
        stream: bool,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": CHAT_TEMPERATURE,
            "timeout": self._timeout,
        }
        if stream:
            kwargs["stream"] = True
            kwargs["stream_options"] = {"include_usage": True}
        if tools:
            kwargs["tools"] = tools
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice
        return kwargs

    @retry(
        reraise=True,
        stop=stop_after_attempt(_RETRY_ATTEMPTS),
        wait=wait_exponential(min=_RETRY_MIN_WAIT_SECONDS, max=_RETRY_MAX_WAIT_SECONDS),
        retry=retry_if_exception_type(APIError) & retry_if_exception(_retryable_api_error),
    )
    def _create_completion(self, **kwargs: Any) -> Any:
        return self.client.chat.completions.create(**kwargs)

    def ask(
        self,
        user_input: str,
        context: str = "",
        conversation_messages: list[dict] | None = None,
        scenario_context: str = "",
    ) -> dict[str, Any]:
        """Call the chat completion API.

        Returns a dict with ``answer`` (assistant text) and ``completion`` (full
        JSON-serializable completion payload from the stack, including ``usage``).
        """
        if not self.base_url:
            return {"answer": NO_ENDPOINT_ANSWER, "completion": None}

        messages = self.build_messages(
            user_input, context, conversation_messages, scenario_context
        )
        self.log_chat_request(streaming=False, message_count=len(messages))
        try:
            completion = self._create_completion(
                **self.completion_kwargs(messages, stream=False),
            )
            text = completion.choices[0].message.content or EMPTY_COMPLETION_ANSWER
            logger.info(
                "LlamaStackChatClient[%s]: response received — model=%s finish_reason=%s",
                self.label,
                completion.model,
                completion.choices[0].finish_reason,
            )
            return {
                "answer": text,
                "completion": self.completion_to_json(completion),
            }
        except APIError as exc:
            logger.error("LlamaStackChatClient[%s]: request failed: %s", self.label, exc)
            return {
                "answer": f"Darn! Something went wrong: {exc}",
                "completion": None,
            }

    def ask_stream(
        self,
        user_input: str,
        context: str = "",
        conversation_messages: list[dict] | None = None,
        scenario_context: str = "",
    ) -> Iterator[dict[str, Any]]:
        """Stream chat completion events for SSE relay.

        Yields ``{"type": "delta", "content": "..."}`` per token chunk and a final
        ``{"type": "done", "answer": "...", "completion": {...}}``.
        """
        if not self.base_url:
            yield {"type": "done", "answer": NO_ENDPOINT_ANSWER, "completion": None}
            return

        messages = self.build_messages(
            user_input, context, conversation_messages, scenario_context
        )
        self.log_chat_request(streaming=True, message_count=len(messages))
        try:
            stream = self._create_completion(
                **self.completion_kwargs(messages, stream=True),
            )
            yield from self.iter_stream_events(stream)
        except APIError as exc:
            yield from self.stream_error_events(exc, label=self.label)

    def iter_stream_events(self, stream: Any) -> Iterator[dict[str, Any]]:
        accumulator = _StreamAccumulator()
        for chunk in stream:
            delta = accumulator.absorb_chunk(chunk, self.completion_to_json)
            if delta:
                yield {"type": "delta", "content": delta}

        logger.info(
            "LlamaStackChatClient[%s]: stream complete — model=%s chars=%d",
            self.label,
            accumulator.completion.get("model", self.model),
            len(accumulator.answer),
        )
        yield {
            "type": "done",
            "answer": accumulator.answer,
            "completion": accumulator.completion or None,
        }

    @staticmethod
    def stream_error_events(exc: Exception, *, label: str) -> Iterator[dict[str, Any]]:
        logger.error("LlamaStackChatClient[%s]: stream failed: %s", label, exc)
        yield {"type": "error", "message": str(exc)}
        yield {
            "type": "done",
            "answer": f"Darn! Something went wrong: {exc}",
            "completion": None,
        }
