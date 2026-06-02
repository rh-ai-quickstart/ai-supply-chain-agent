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


def test_ask_stream_config_error_when_base_url_cleared():
    client = LlamaStackClient.__new__(LlamaStackClient)
    client.base_url = ""
    client._client = MagicMock()
    client.model = "x"
    parts = list(client.ask_stream("hi"))
    assert len(parts) == 1
    assert "endpoint" in parts[0][0].lower()
    client._client.chat.completions.create.assert_not_called()


def test_build_messages_includes_context_and_history():
    msgs = LlamaStackClient._build_messages(
        "fallback",
        context="ctx",
        conversation_messages=[{"role": "user", "content": "hi"}],
    )
    assert msgs[0]["role"] == "system"
    assert "ctx" in msgs[1]["content"]
    assert msgs[-1] == {"role": "user", "content": "hi"}


def test_ask_stream_yields_error_message_on_failure():
    client = LlamaStackClient.__new__(LlamaStackClient)
    client.base_url = "http://stack/v1/openai/v1"
    client.model = "test-model"
    client._timeout = 30
    mock_openai_client = MagicMock()
    mock_openai_client.chat.completions.create.side_effect = RuntimeError("upstream down")
    client._client = mock_openai_client

    parts = list(client.ask_stream("question"))
    assert len(parts) == 1
    assert "upstream down" in parts[0][0]
    assert parts[0][1] is None


def test_ask_stream_yields_deltas_and_completion():
    chunk1 = MagicMock()
    chunk1.choices = [MagicMock(delta=MagicMock(content="Hi"))]
    chunk2 = MagicMock()
    chunk2.choices = [MagicMock(delta=MagicMock(content=None))]
    chunk2.model_dump.return_value = {"id": "stream-1", "model": "test-model"}

    client = LlamaStackClient.__new__(LlamaStackClient)
    client.base_url = "http://stack/v1/openai/v1"
    client.model = "test-model"
    client._timeout = 30
    mock_openai_client = MagicMock()
    mock_openai_client.chat.completions.create.return_value = iter([chunk1, chunk2])
    client._client = mock_openai_client

    parts = list(client.ask_stream("question"))
    assert parts[0] == ("Hi", None)
    assert parts[-1][0] == ""
    assert parts[-1][1]["id"] == "stream-1"
    mock_openai_client.chat.completions.create.assert_called_once()
    assert mock_openai_client.chat.completions.create.call_args.kwargs["stream"] is True
