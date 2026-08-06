"""``RagContextProvider`` retrieval branches."""

from unittest.mock import MagicMock

from services.rag_context_provider import RagContextProvider


def test_uses_llama_stack_vector_search_when_vector_store_id_given():
    llama = MagicMock()
    llama.search_vector_store.return_value = "chunk text"
    provider = RagContextProvider(llama, vector_store_client=None)
    out = provider.get_context("supplier risk", vector_store_id="vs_1")
    assert out == "chunk text"
    llama.search_vector_store.assert_called_once_with("vs_1", "supplier risk", max_num_results=8)


def test_returns_empty_when_no_vector_store_selected_and_no_fallback_client():
    llama = MagicMock()
    provider = RagContextProvider(llama, vector_store_client=None)
    assert provider.get_context("query") == ""
    llama.search_vector_store.assert_not_called()


def test_falls_back_to_pgvector_similarity_search():
    llama = MagicMock()
    doc = MagicMock()
    doc.page_content = "doc a"
    vs_client = MagicMock()
    vs_client.similarity_search.return_value = [doc]
    provider = RagContextProvider(llama, vector_store_client=vs_client)
    out = provider.get_context("query text")
    assert out == "doc a"
    vs_client.similarity_search.assert_called_once_with("query text", k=3)


def test_pgvector_failure_degrades_to_empty_context():
    llama = MagicMock()
    vs_client = MagicMock()
    vs_client.similarity_search.side_effect = RuntimeError("db down")
    provider = RagContextProvider(llama, vector_store_client=vs_client)
    assert provider.get_context("query text") == ""
