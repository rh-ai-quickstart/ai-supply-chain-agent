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
