"""``LlamaStackClient`` helpers without calling a real stack."""

from unittest.mock import MagicMock

from clients.llama_stack_client import LlamaStackClient


def test_completion_to_json_none():
    assert LlamaStackClient._completion_to_json(None) == {}


def test_completion_to_json_uses_model_dump():
    completion = MagicMock()
    completion.model_dump.return_value = {"id": "c1"}
    out = LlamaStackClient._completion_to_json(completion)
    assert out == {"id": "c1"}


def test_ask_returns_config_error_when_base_url_cleared():
    client = LlamaStackClient.__new__(LlamaStackClient)
    client.base_url = ""
    client._client = MagicMock()
    client.model = "x"
    out = client.ask("hi")
    assert "endpoint" in out["answer"].lower()
    client._client.chat.completions.create.assert_not_called()
