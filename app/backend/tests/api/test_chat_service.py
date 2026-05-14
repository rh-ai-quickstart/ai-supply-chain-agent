"""Tests for ``ChatService`` guardrails, routing branch, RAG, and history mapping."""

from unittest.mock import MagicMock

import pytest

from services.chat_service import ChatService, _GUARDRAIL_RESPONSE


@pytest.fixture
def chat_service(mock_llama_stack_client, mock_route_service):
    return ChatService(mock_llama_stack_client, mock_route_service, vector_store_client=None)


def test_guardrail_blocks_off_topic(chat_service):
    out = chat_service.reply("Do you know a good pizza place?", chat_history=[])
    assert out["answer"] == _GUARDRAIL_RESPONSE
    mock_llama = chat_service.llama_stack_client
    mock_llama.ask.assert_not_called()


def test_route_query_uses_route_service(chat_service, mock_route_service):
    mock_route_service.is_route_query.return_value = True
    mock_route_service.get_optimized_route.return_value = {
        "answer": "Calculated route.",
        "routeData": {"type": "optimized_land_route", "coordinates": [[0, 0], [1, 1]]},
    }
    out = chat_service.reply("Find the best truck route", chat_history=[])
    assert out["answer"] == "Calculated route."
    assert "routeData" in out
    mock_route_service.get_optimized_route.assert_called_once()
    chat_service.llama_stack_client.ask.assert_not_called()


def test_reply_uses_llama_with_context_from_vector_store_id(
    chat_service, mock_llama_stack_client, mock_route_service
):
    mock_route_service.is_route_query.return_value = False
    out = chat_service.reply(
        "Summarize supplier risk",
        chat_history=[],
        vector_store_id="vs_abc",
    )
    assert out["answer"] == "mocked answer"
    mock_llama_stack_client.search_vector_store.assert_called_once_with(
        "vs_abc", "Summarize supplier risk", max_num_results=8
    )
    mock_llama_stack_client.ask.assert_called_once()
    call_kw = mock_llama_stack_client.ask.call_args.kwargs
    assert call_kw["context"] == "context chunk"


def test_latest_user_text_prefers_history():
    mock_llama = MagicMock()
    mock_llama.ask.return_value = {"answer": "ok", "completion": None}
    mock_route = MagicMock()
    mock_route.is_route_query.return_value = False
    svc = ChatService(mock_llama, mock_route, vector_store_client=None)
    history = [
        {"role": "human", "content": "first"},
        {"role": "ai", "content": "mid"},
        {"role": "human", "content": "  latest question  "},
    ]
    svc.reply("ignored fallback", chat_history=history)
    mock_llama.ask.assert_called_once()
    assert mock_llama.ask.call_args.args[0] == "latest question"


def test_map_chat_history_roles():
    history = [
        {"role": "human", "content": "hi"},
        {"role": "ai", "content": "hello"},
        {"role": "system", "content": "skip"},
        {"role": "human", "content": ""},
    ]
    mapped = ChatService._map_chat_history(history)
    assert mapped == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]


def test_retrieve_context_via_pgvector_client_fallback():
    mock_llama = MagicMock()
    mock_route = MagicMock()
    doc = MagicMock()
    doc.page_content = "doc a"
    vs = MagicMock()
    vs.similarity_search.return_value = [doc]
    svc = ChatService(mock_llama, mock_route, vector_store_client=vs)
    mock_route.is_route_query.return_value = False
    svc.reply("query text", chat_history=[], vector_store_id=None)
    vs.similarity_search.assert_called_once_with("query text", k=3)
    ctx = mock_llama.ask.call_args.kwargs["context"]
    assert ctx == "doc a"
