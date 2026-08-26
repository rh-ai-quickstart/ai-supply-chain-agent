from clients.embedding_client import openai_embeddings_kwargs


def test_openai_embeddings_kwargs_uses_llama_stack_by_default():
    kwargs = openai_embeddings_kwargs(
        llama_stack_url="http://llamastack:8321",
        embed_model="sentence-transformers/nomic-ai/nomic-embed-text-v1.5",
    )
    assert kwargs["base_url"] == "http://llamastack:8321/v1"
    assert kwargs["api_key"] == "not-required"
    assert kwargs["model"] == "sentence-transformers/nomic-ai/nomic-embed-text-v1.5"


def test_openai_embeddings_kwargs_uses_direct_maas_when_configured():
    kwargs = openai_embeddings_kwargs(
        llama_stack_url="http://llamastack:8321",
        embed_model="nomic-embed-text-v1-5",
        embed_base_url="https://maas.example.com/v1",
        embed_api_key="sk-test",
    )
    assert kwargs["base_url"] == "https://maas.example.com/v1"
    assert kwargs["api_key"] == "sk-test"
    assert kwargs["model"] == "nomic-embed-text-v1-5"
