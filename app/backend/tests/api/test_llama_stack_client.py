"""``LlamaStackClient`` helpers without calling a real stack."""

import os
from unittest.mock import MagicMock, patch

from clients.llama_stack_client import LlamaStackClient, timeout_seconds_from_env


def test_completion_to_json_none():
    assert LlamaStackClient._completion_to_json(None) == {}


def test_completion_to_json_uses_model_dump():
    completion = MagicMock()
    completion.model_dump.return_value = {"id": "c1"}
    out = LlamaStackClient._completion_to_json(completion)
    assert out == {"id": "c1"}


def test_timeout_seconds_from_env_default(monkeypatch):
    monkeypatch.delenv("LLAMA_STACK_TIMEOUT_SECONDS", raising=False)
    assert timeout_seconds_from_env() == 300


def test_timeout_seconds_from_env_override(monkeypatch):
    monkeypatch.setenv("LLAMA_STACK_TIMEOUT_SECONDS", "120")
    assert timeout_seconds_from_env() == 120


def test_client_uses_env_timeout(monkeypatch):
    monkeypatch.setenv("LLAMA_STACK_TIMEOUT_SECONDS", "90")
    with patch("clients.llama_stack_client.OpenAI") as mock_openai:
        LlamaStackClient()
    assert mock_openai.call_args.kwargs["timeout"] == 90


def test_ask_returns_config_error_when_base_url_cleared():
    client = LlamaStackClient.__new__(LlamaStackClient)
    client.base_url = ""
    client._client = MagicMock()
    client.model = "x"
    out = client.ask("hi")
    assert "endpoint" in out["answer"].lower()
    client._client.chat.completions.create.assert_not_called()


def test_ask_stream_yields_done_when_base_url_cleared():
    client = LlamaStackClient.__new__(LlamaStackClient)
    client.base_url = ""
    client._client = MagicMock()
    client.model = "x"
    events = list(client.ask_stream("hi"))
    assert events == [
        {
            "type": "done",
            "answer": "Something went wrong. There is no endpoint configured.",
            "completion": None,
        }
    ]
    client._client.chat.completions.create.assert_not_called()


def test_ask_stream_yields_delta_and_done():
    client = LlamaStackClient.__new__(LlamaStackClient)
    client.base_url = "http://stack/v1"
    client.label = "test"
    client.model = "test-model"
    client._timeout = 30
    client._client = MagicMock()

    chunk1 = MagicMock()
    chunk1.usage = None
    chunk1.model = "test-model"
    chunk1.choices = [MagicMock(delta=MagicMock(content="Hello"), finish_reason=None)]

    chunk2 = MagicMock()
    chunk2.usage = MagicMock()
    chunk2.usage.model_dump.return_value = {"total_tokens": 5}
    chunk2.model = "test-model"
    chunk2.choices = [MagicMock(delta=MagicMock(content=" world"), finish_reason="stop")]

    client._client.chat.completions.create.return_value = iter([chunk1, chunk2])

    with patch.object(LlamaStackClient, "_build_messages", return_value=[{"role": "user", "content": "hi"}]):
        events = list(client.ask_stream("hi"))

    assert events[0] == {"type": "delta", "content": "Hello"}
    assert events[1] == {"type": "delta", "content": " world"}
    assert events[2]["type"] == "done"
    assert events[2]["answer"] == "Hello world"
    assert events[2]["completion"]["usage"] == {"total_tokens": 5}
    create_kwargs = client._client.chat.completions.create.call_args.kwargs
    assert create_kwargs["stream"] is True
    assert create_kwargs["stream_options"] == {"include_usage": True}


def test_stream_accumulator_absorbs_chunks():
    from clients.llama_stack_client import _StreamAccumulator

    acc = _StreamAccumulator()
    chunk = MagicMock()
    chunk.usage = None
    chunk.model = "m1"
    chunk.choices = [MagicMock(delta=MagicMock(content="tok"), finish_reason="stop")]

    delta = acc.absorb_chunk(chunk, LlamaStackClient._completion_to_json)

    assert delta == "tok"
    assert acc.answer == "tok"
    assert acc.completion["model"] == "m1"
    assert acc.completion["finish_reason"] == "stop"


def test_ask_with_tools_executes_tool_then_returns_final_answer():
    client = LlamaStackClient.__new__(LlamaStackClient)
    client.base_url = "http://stack/v1"
    client.label = "test"
    client.model = "test-model"
    client._timeout = 30
    client._client = MagicMock()

    tool_call = MagicMock()
    tool_call.id = "call_1"
    tool_call.function.name = "fetch_news"
    tool_call.function.arguments = '{"limit": 5}'

    first = MagicMock()
    first.model = "test-model"
    first.choices = [MagicMock(message=MagicMock(content=None, tool_calls=[tool_call]))]
    first.model_dump.return_value = {"id": "c1"}

    second = MagicMock()
    second.model = "test-model"
    second.choices = [
        MagicMock(message=MagicMock(content="Here are the headlines.", tool_calls=None))
    ]
    second.model_dump.return_value = {"id": "c2"}

    client._client.chat.completions.create.side_effect = [first, second]
    executed = []

    def execute_tool(name, args):
        executed.append((name, args))
        return "headline list"

    with patch.object(
        LlamaStackClient,
        "_build_messages",
        return_value=[{"role": "user", "content": "news?"}],
    ):
        out = client.ask_with_tools(
            "news?",
            tools=[{"type": "function", "function": {"name": "fetch_news"}}],
            execute_tool=execute_tool,
        )

    assert out["answer"] == "Here are the headlines."
    assert executed == [("fetch_news", {"limit": 5})]
    assert out["tool_calls_made"][0]["name"] == "fetch_news"
    assert client._client.chat.completions.create.call_count == 2


def test_ask_with_tools_without_tools_falls_back_to_ask():
    client = LlamaStackClient.__new__(LlamaStackClient)
    client.base_url = "http://stack/v1"
    client.label = "test"
    client.model = "test-model"
    client._timeout = 30
    client._client = MagicMock()
    with patch.object(client, "ask", return_value={"answer": "plain", "completion": None}) as ask:
        out = client.ask_with_tools("hi", tools=None, execute_tool=None)
    ask.assert_called_once()
    assert out["answer"] == "plain"
    assert out["tool_calls_made"] == []


def test_build_messages_uses_single_leading_system_message():
    """Qwen / LiteMaaS reject a second role=system mid-list."""
    client = LlamaStackClient.__new__(LlamaStackClient)
    messages = client._build_messages(
        "what about ports?",
        context="Port strike risk is elevated.",
        conversation_messages=None,
    )
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert "supply chain command center" in messages[0]["content"]
    assert "Port strike risk is elevated." in messages[0]["content"]
    assert messages[1] == {"role": "user", "content": "what about ports?"}
    assert sum(1 for m in messages if m["role"] == "system") == 1


def test_build_messages_drops_system_turns_from_history():
    client = LlamaStackClient.__new__(LlamaStackClient)
    messages = client._build_messages(
        "ignored when history present",
        context="",
        conversation_messages=[
            {"role": "system", "content": "should drop"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ],
    )
    assert messages[0]["role"] == "system"
    assert [m["role"] for m in messages[1:]] == ["user", "assistant"]
    assert all(m["role"] != "system" for m in messages[1:])
