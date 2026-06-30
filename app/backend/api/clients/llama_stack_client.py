import io
import logging
import os
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an AI assistant for a supply chain command center. "
    "You help operators understand logistics data, demand forecasting, "
    "inventory levels, supplier risk, and shipping routes. "
    "Answer concisely and only about supply chain topics. "
    "If asked about unrelated topics, politely redirect to supply chain matters."
)

_NO_ENDPOINT_ANSWER = "Something went wrong. There is no endpoint configured."
_EMPTY_COMPLETION_ANSWER = "Darn! Something went wrong."
_CHAT_TEMPERATURE = 0.1

# Default matches frontend nginx proxy_read_timeout (300s) for slow CPU/GPU inference.
_DEFAULT_TIMEOUT_SECONDS = 300


def timeout_seconds_from_env(default: int = _DEFAULT_TIMEOUT_SECONDS) -> int:
    """Read ``LLAMA_STACK_TIMEOUT_SECONDS`` (integer seconds)."""
    raw = os.getenv("LLAMA_STACK_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        logger.warning(
            "Invalid LLAMA_STACK_TIMEOUT_SECONDS=%r; using default %s",
            raw,
            default,
        )
        return default


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
        return "".join(self.parts) or _EMPTY_COMPLETION_ANSWER


class LlamaStackClient:
    """OpenAI-compatible client pointed at a Llama Stack server."""

    def __init__(
        self,
        timeout_seconds: int | None = None,
        base_url: str | None = None,
        model: str | None = None,
        label: str = "vllm",
    ):
        env_url = os.getenv("LLAMA_STACK_URL", "http://llamastack:8321")
        self.base_url = (base_url or env_url).rstrip("/") + "/v1"
        self.label = label
        self.model = model or os.getenv(
            "LLAMA_STACK_MODEL",
            "llama-3-2-1b-instruct/meta-llama/Llama-3.2-1B-Instruct",
        )
        self._timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else timeout_seconds_from_env()
        )

        self._client = OpenAI(
            api_key="not-required",
            base_url=self.base_url,
            timeout=self._timeout,
        )
        logger.info(
            "LlamaStackClient[%s]: base_url=%s model=%s timeout=%ss "
            "(LLAMA_STACK_TIMEOUT_SECONDS for slow inference)",
            self.label,
            self.base_url,
            self.model,
            self._timeout,
        )

    def _build_messages(
        self,
        user_input: str,
        context: str = "",
        conversation_messages: list[dict] | None = None,
    ) -> list[dict]:
        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

        if context:
            messages.append(
                {
                    "role": "system",
                    "content": f"Relevant context from the knowledge base:\n{context}",
                }
            )

        turns = conversation_messages if conversation_messages else []
        if turns:
            messages.extend(turns)
        else:
            messages.append({"role": "user", "content": user_input})

        return messages

    @staticmethod
    def _completion_to_json(completion: Any) -> dict[str, Any]:
        """Serialize an OpenAI ``ChatCompletion`` (or similar) for API responses."""
        if completion is None:
            return {}
        try:
            dumped = completion.model_dump(mode="json")
            return dumped if isinstance(dumped, dict) else {"value": dumped}
        except Exception as exc:
            logger.warning("LlamaStackClient: could not model_dump completion: %s", exc)
            return {"serialization_error": str(exc)}

    def _log_chat_request(self, *, streaming: bool, message_count: int) -> None:
        mode = "streaming" if streaming else "sending"
        logger.info(
            "LlamaStackClient[%s]: %s request — base_url=%s model=%s message_count=%d",
            self.label,
            mode,
            self.base_url,
            self.model,
            message_count,
        )

    def _completion_kwargs(self, messages: list[dict], *, stream: bool) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": _CHAT_TEMPERATURE,
            "timeout": self._timeout,
        }
        if stream:
            kwargs["stream"] = True
            kwargs["stream_options"] = {"include_usage": True}
        return kwargs

    def _iter_stream_events(self, stream: Any) -> Iterator[dict[str, Any]]:
        accumulator = _StreamAccumulator()
        for chunk in stream:
            delta = accumulator.absorb_chunk(chunk, self._completion_to_json)
            if delta:
                yield {"type": "delta", "content": delta}

        logger.info(
            "LlamaStackClient[%s]: stream complete — model=%s chars=%d",
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
    def _stream_error_events(exc: Exception, *, label: str) -> Iterator[dict[str, Any]]:
        logger.error("LlamaStackClient[%s]: stream failed: %s", label, exc)
        yield {"type": "error", "message": str(exc)}
        yield {
            "type": "done",
            "answer": f"Darn! Something went wrong: {exc}",
            "completion": None,
        }

    def ask(
        self,
        user_input: str,
        context: str = "",
        conversation_messages: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Call the chat completion API.

        Returns a dict with ``answer`` (assistant text) and ``completion`` (full
        JSON-serializable completion payload from the stack, including ``usage``).
        """
        if not self.base_url:
            return {"answer": _NO_ENDPOINT_ANSWER, "completion": None}

        messages = self._build_messages(user_input, context, conversation_messages)
        self._log_chat_request(streaming=False, message_count=len(messages))
        try:
            completion = self._client.chat.completions.create(
                **self._completion_kwargs(messages, stream=False),
            )
            text = completion.choices[0].message.content or _EMPTY_COMPLETION_ANSWER
            logger.info(
                "LlamaStackClient[%s]: response received — model=%s finish_reason=%s",
                self.label,
                completion.model,
                completion.choices[0].finish_reason,
            )
            return {
                "answer": text,
                "completion": self._completion_to_json(completion),
            }
        except Exception as exc:
            logger.error("LlamaStackClient[%s]: request failed: %s", self.label, exc)
            return {
                "answer": f"Darn! Something went wrong: {exc}",
                "completion": None,
            }

    def ask_stream(
        self,
        user_input: str,
        context: str = "",
        conversation_messages: list[dict] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Stream chat completion events for SSE relay.

        Yields ``{"type": "delta", "content": "..."}`` per token chunk and a final
        ``{"type": "done", "answer": "...", "completion": {...}}``.
        """
        if not self.base_url:
            yield {"type": "done", "answer": _NO_ENDPOINT_ANSWER, "completion": None}
            return

        messages = self._build_messages(user_input, context, conversation_messages)
        self._log_chat_request(streaming=True, message_count=len(messages))
        try:
            stream = self._client.chat.completions.create(
                **self._completion_kwargs(messages, stream=True),
            )
            yield from self._iter_stream_events(stream)
        except Exception as exc:
            yield from self._stream_error_events(exc, label=self.label)

    def list_vector_stores(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return vector stores from LlamaStack (OpenAI-compatible ``/vector_stores``)."""
        out: list[dict[str, Any]] = []
        try:
            page = self._client.vector_stores.list(limit=min(limit, 100), order="desc")
            for vs in page.data:
                out.append(
                    {
                        "id": vs.id,
                        "name": vs.name or vs.id,
                        "status": getattr(vs, "status", None),
                        "created_at": vs.created_at,
                    }
                )
        except Exception as exc:
            logger.warning("LlamaStack list vector_stores failed: %s", exc)
        return out

    def search_vector_store(
        self,
        vector_store_id: str,
        query: str,
        *,
        max_num_results: int = 8,
    ) -> str:
        """Run vector store search; returns concatenated chunk text for RAG."""
        if not vector_store_id or not (query or "").strip():
            return ""
        try:
            page = self._client.vector_stores.search(
                vector_store_id,
                query=query.strip(),
                max_num_results=min(max(max_num_results, 1), 50),
            )
            parts: list[str] = []
            for row in page.data:
                for block in row.content:
                    if getattr(block, "type", None) == "text":
                        text = getattr(block, "text", "") or ""
                        if text.strip():
                            parts.append(text.strip())
            return "\n\n".join(parts)
        except Exception as exc:
            logger.warning(
                "LlamaStack vector_stores.search failed store=%s: %s",
                vector_store_id,
                exc,
            )
            return ""

    def create_vector_store(self, name: str) -> str:
        """Create a LlamaStack vector store; returns the server-assigned id."""
        provider = os.getenv("VECTOR_STORE_PROVIDER", "pgvector")
        vector_store = self._client.vector_stores.create(
            name=name,
            extra_body={"provider_id": provider},
        )
        logger.info("LlamaStackClient: created vector store id=%s name=%s", vector_store.id, name)
        return str(vector_store.id)

    def upload_file_bytes(self, filename: str, content: bytes) -> str:
        """Upload file bytes to LlamaStack; returns file id."""
        buffer = io.BytesIO(content)
        response = self._client.files.create(
            file=(filename, buffer),
            purpose="assistants",
        )
        logger.info("LlamaStackClient: uploaded file id=%s name=%s", response.id, filename)
        return str(response.id)

    def attach_file_to_vector_store(self, vector_store_id: str, file_id: str) -> None:
        """Attach an uploaded file to a vector store (triggers server-side chunk/embed)."""
        self._client.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_id,
        )
        logger.info(
            "LlamaStackClient: attached file_id=%s to vector_store_id=%s",
            file_id,
            vector_store_id,
        )
