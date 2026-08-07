"""Composition-root wiring for ``Container`` and ``Settings.from_env``."""

from unittest.mock import MagicMock, patch

from container import Container, _build_primary_llama_client, _resolve_openai_model
from settings import Settings


def test_resolve_openai_model_uses_settings_then_fallback():
    assert _resolve_openai_model(Settings(llama_stack_openai_model="external-model/x")) == (
        "external-model/x"
    )
    assert _resolve_openai_model(Settings(llama_stack_openai_model="")) == "gpt-4o-mini"


def test_build_primary_llama_client_uses_openai_model_for_openai_url():
    settings = Settings(
        llama_stack_url="https://api.openai.com/v1",
        llama_stack_model="llama-stack-model-id",
        llama_stack_openai_model="gpt-4o-mini",
    )
    client = _build_primary_llama_client(settings, "gpt-4o-mini")
    assert client.model == "gpt-4o-mini"
    assert client.label == "vllm"


def test_build_primary_llama_client_uses_stack_model_otherwise():
    settings = Settings(
        llama_stack_url="http://llamastack:8321",
        llama_stack_model="stack-model",
    )
    client = _build_primary_llama_client(settings, "gpt-4o-mini")
    assert client.model == "stack-model"


def test_settings_from_env_reads_core_overrides(monkeypatch):
    monkeypatch.setenv("GENERAL_SIMULATION_BASE_URL", "http://gen-sim:8000")
    monkeypatch.setenv("GENERAL_SIMULATION_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("NEWS_FEED_URLS", "BBC|https://example/rss")
    monkeypatch.setenv("LLAMA_STACK_OPENAI_MODEL", "external-model/Qwen")
    monkeypatch.setenv("KNOWLEDGE_BASES_STORE_PATH", "/tmp/kb-test.json")
    monkeypatch.setenv("GIT_COMMIT", "abc123")
    settings = Settings.from_env()
    assert settings.general_simulation_base_url == "http://gen-sim:8000"
    assert settings.general_simulation_timeout_seconds == 45
    assert settings.news_feed_urls_raw == "BBC|https://example/rss"
    assert settings.llama_stack_openai_model == "external-model/Qwen"
    assert settings.knowledge_bases_store_path == "/tmp/kb-test.json"
    assert settings.git_commit == "abc123"


@patch("container.VectorStoreClient", side_effect=RuntimeError("no pg"))
def test_container_injects_shared_clients_into_chat_agent(_mock_vs):
    settings = Settings(
        llama_stack_url="http://llamastack:8321",
        llama_stack_model="stack-model",
        llama_stack_openai_model="openai-model",
        general_simulation_base_url="http://gen-sim:8000",
        general_simulation_timeout_seconds=33,
        knowledge_bases_store_path="/tmp/kb-container-test.json",
    )
    container = Container(settings)

    assert container.vector_store_client is None
    assert container.chat_service.agent_service is container.agent_service
    assert container.chat_service.openai_client is container.openai_llama_client
    assert container.agent_service._sim_service._client is container.general_simulation_client
    assert container.agent_service._news_service._client is container.news_client
    assert container.general_simulation_client.base_url == "http://gen-sim:8000"
    assert container.general_simulation_client.timeout == 33
    assert container.scenario_create_service is not None
    assert container.readiness_service is not None
    assert container.primary_llama_client.model == "stack-model"
    assert container.openai_llama_client.model == "openai-model"
    assert container.openai_llama_client.label == "openai"
