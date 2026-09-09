"""``RagContextProvider`` retrieval branches."""

from unittest.mock import MagicMock

from services.rag_context_provider import RagContextProvider


def test_uses_llama_stack_vector_search_when_vector_store_id_given():
    llama = MagicMock()
    llama.search_vector_store.return_value = "chunk text"
    provider = RagContextProvider(llama)
    out = provider.get_context("supplier risk", vector_store_id="vs_1")
    assert out == "chunk text"
    llama.search_vector_store.assert_called_once_with("vs_1", "supplier risk", max_num_results=8)


def test_returns_empty_when_no_vector_store_selected():
    llama = MagicMock()
    provider = RagContextProvider(llama)
    assert provider.get_context("query") == ""
    llama.search_vector_store.assert_not_called()


def test_vector_store_failure_degrades_to_empty_context():
    llama = MagicMock()
    llama.search_vector_store.side_effect = RuntimeError("store down")
    provider = RagContextProvider(llama)
    assert provider.get_context("query text", vector_store_id="vs_1") == ""
