"""Agentic tool-calling loop layered on top of a plain chat-completion client.

Split out of the former monolithic ``LlamaStackClient`` (SRP). This class is
composed with a ``LlamaStackChatClient`` (has-a, not is-a) so any compatible
chat-completion client can drive the loop.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any

from clients.chat_completion_client import EMPTY_COMPLETION_ANSWER, NO_ENDPOINT_ANSWER, LlamaStackChatClient
from logging_config import getLogger
from openai import APIError

logger = getLogger(__name__)

DEFAULT_TOOL_MAX_ROUNDS = 3


class ToolLoopOrchestrator:
    """Runs an OpenAI-style tool-calling loop against a ``LlamaStackChatClient``."""

    def __init__(self, chat_client: LlamaStackChatClient):
        self._chat = chat_client

    @property
    def label(self) -> str:
        return self._chat.label

    @property
    def model(self) -> str:
        return self._chat.model

    @property
    def base_url(self) -> str:
        return self._chat.base_url

    @staticmethod
    def _assistant_message_dict(message: Any) -> dict[str, Any]:
        """Serialize an OpenAI assistant message (including tool_calls) for the next turn."""
        payload: dict[str, Any] = {
            "role": "assistant",
            "content": message.content,
        }
        tool_calls = getattr(message, "tool_calls", None) or []
        if tool_calls:
            serialized = []
            for tc in tool_calls:
                serialized.append(
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments or "{}",
                        },
                    }
                )
            payload["tool_calls"] = serialized
        return payload

    @staticmethod
    def _parse_tool_arguments(raw: str | None) -> dict[str, Any]:
        if not raw or not str(raw).strip():
            return {}
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            logger.warning("ToolLoopOrchestrator: invalid tool arguments JSON: %r", raw)
            return {}

    def _execute_tool_round(
        self,
        message: Any,
        execute_tool: Callable[[str, dict[str, Any]], str],
        tool_calls_made: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Run each tool_call; return tool-role messages to append."""
        tool_messages: list[dict[str, Any]] = []
        for tc in message.tool_calls or []:
            name = tc.function.name
            args = self._parse_tool_arguments(tc.function.arguments)
            logger.info("ToolLoopOrchestrator[%s]: executing tool %s", self.label, name)
            try:
                result_text = execute_tool(name, args)
            except Exception as exc:
                logger.error("ToolLoopOrchestrator[%s]: tool %s raised: %s", self.label, name, exc)
                result_text = f"Error running tool {name}: {exc}"
            summary = (result_text or "")[:500]
            tool_calls_made.append(
                {"name": name, "args": args, "result_summary": summary}
            )
            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_text or "",
                }
            )
        return tool_messages

    def _create_completion(
        self,
        messages: list[dict],
        *,
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
    ) -> Any:
        """Log and issue one completion request against the chat client."""
        self._chat.log_chat_request(streaming=stream, message_count=len(messages))
        kwargs = self._chat.completion_kwargs(
            messages, stream=stream, tools=tools, tool_choice="auto" if tools else None
        )
        return self._chat._create_completion(**kwargs)

    @staticmethod
    def _final_result(
        completion: Any, tool_calls_made: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Build the standard ``ask_with_tools`` result dict from a completion."""
        text = completion.choices[0].message.content or EMPTY_COMPLETION_ANSWER
        return {
            "answer": text,
            "completion": LlamaStackChatClient.completion_to_json(completion),
            "tool_calls_made": tool_calls_made,
        }

    @staticmethod
    def _tool_names(message: Any) -> list[str]:
        """The tool call names requested by the model in this message."""
        return [tc.function.name for tc in message.tool_calls or []]

    def ask_with_tools(
        self,
        user_input: str,
        context: str = "",
        conversation_messages: list[dict] | None = None,
        tools: list[dict[str, Any]] | None = None,
        execute_tool: Callable[[str, dict[str, Any]], str] | None = None,
        max_rounds: int = DEFAULT_TOOL_MAX_ROUNDS,
        scenario_context: str = "",
    ) -> dict[str, Any]:
        """Chat completion with an OpenAI-style tool loop.

        Returns ``answer``, ``completion``, and ``tool_calls_made``.
        """
        if not self.base_url:
            return {
                "answer": NO_ENDPOINT_ANSWER,
                "completion": None,
                "tool_calls_made": [],
            }

        messages = self._chat.build_messages(
            user_input, context, conversation_messages, scenario_context
        )
        tool_schemas = tools or []
        tool_calls_made: list[dict[str, Any]] = []
        rounds = max(1, int(max_rounds or DEFAULT_TOOL_MAX_ROUNDS))

        if not tool_schemas or execute_tool is None:
            plain = self._chat.ask(
                user_input,
                context=context,
                conversation_messages=conversation_messages,
                scenario_context=scenario_context,
            )
            plain["tool_calls_made"] = []
            return plain

        try:
            for _ in range(rounds):
                completion = self._create_completion(messages, tools=tool_schemas)
                message = completion.choices[0].message
                if not getattr(message, "tool_calls", None):
                    logger.info(
                        "ToolLoopOrchestrator[%s]: tool loop finished — model=%s tools=%d",
                        self.label,
                        completion.model,
                        len(tool_calls_made),
                    )
                    return self._final_result(completion, tool_calls_made)

                messages.append(self._assistant_message_dict(message))
                messages.extend(
                    self._execute_tool_round(message, execute_tool, tool_calls_made)
                )

            # Max rounds with tools exhausted — one final call without tools.
            completion = self._create_completion(messages)
            return self._final_result(completion, tool_calls_made)
        except APIError as exc:
            logger.error("ToolLoopOrchestrator[%s]: ask_with_tools failed: %s", self.label, exc)
            return {
                "answer": f"Darn! Something went wrong: {exc}",
                "completion": None,
                "tool_calls_made": tool_calls_made,
            }

    def ask_stream_with_tools(
        self,
        user_input: str,
        context: str = "",
        conversation_messages: list[dict] | None = None,
        tools: list[dict[str, Any]] | None = None,
        execute_tool: Callable[[str, dict[str, Any]], str] | None = None,
        max_rounds: int = DEFAULT_TOOL_MAX_ROUNDS,
        scenario_context: str = "",
    ) -> Iterator[dict[str, Any]]:
        """Run non-streamed tool rounds, then stream the final assistant answer.

        Yields optional ``{"type": "tool", "name": ...}`` events, then the usual
        ``delta`` / ``done`` events. ``done`` includes ``tool_calls_made``.
        """
        if not self.base_url:
            yield {"type": "done", "answer": NO_ENDPOINT_ANSWER, "completion": None, "tool_calls_made": []}
            return

        tool_schemas = tools or []
        if not tool_schemas or execute_tool is None:
            yield from self._chat.ask_stream(
                user_input,
                context=context,
                conversation_messages=conversation_messages,
                scenario_context=scenario_context,
            )
            return

        messages = self._chat.build_messages(
            user_input, context, conversation_messages, scenario_context
        )
        tool_calls_made: list[dict[str, Any]] = []
        rounds = max(1, int(max_rounds or DEFAULT_TOOL_MAX_ROUNDS))

        try:
            for _ in range(rounds):
                completion = self._create_completion(messages, tools=tool_schemas)
                message = completion.choices[0].message
                if not getattr(message, "tool_calls", None):
                    text = message.content or EMPTY_COMPLETION_ANSWER
                    if text:
                        yield {"type": "delta", "content": text}
                    yield {"type": "done", **self._final_result(completion, tool_calls_made)}
                    return

                for name in self._tool_names(message):
                    yield {"type": "tool", "name": name}

                messages.append(self._assistant_message_dict(message))
                messages.extend(
                    self._execute_tool_round(message, execute_tool, tool_calls_made)
                )

            # Stream final answer after tool results (no tools on this call).
            stream = self._create_completion(messages, stream=True)
            for event in self._chat.iter_stream_events(stream):
                if event.get("type") == "done":
                    event = {**event, "tool_calls_made": tool_calls_made}
                yield event
        except APIError as exc:
            for event in self._chat.stream_error_events(exc, label=self.label):
                if event.get("type") == "done":
                    event = {**event, "tool_calls_made": tool_calls_made}
                yield event
