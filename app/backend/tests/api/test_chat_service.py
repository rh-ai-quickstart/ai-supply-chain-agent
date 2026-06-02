"""Tests for ``ChatService`` guardrails, routing branch, RAG, and history mapping."""

from unittest.mock import MagicMock

import pytest

from services.chat_service import ChatService, _GUARDRAIL_RESPONSE


@pytest.fixture
def chat_service(mock_llama_stack_client, mock_route_service):
    return ChatService(mock_llama_stack_client, mock_route_service, vector_store_client=None)


def test_reply_stream_guardrail_emits_message(chat_service):
    events = list(
        chat_service.reply_stream("Do you know a good pizza place?", chat_history=[])
    )
    assert events == [
        {"event": "message", "answer": _GUARDRAIL_RESPONSE, "completion": None}
    ]
    chat_service.llama_stack_client.ask_stream.assert_not_called()


def test_reply_stream_route_emits_message(chat_service, mock_route_service):
    mock_route_service.is_route_query.return_value = True
    mock_route_service.get_optimized_route.return_value = {
        "answer": "Calculated route.",
        "routeData": {"type": "optimized_land_route", "coordinates": [[0, 0], [1, 1]]},
    }
    events = list(chat_service.reply_stream("Find the best truck route", chat_history=[]))
    assert len(events) == 1
    assert events[0]["event"] == "message"
    assert events[0]["answer"] == "Calculated route."
    assert "routeData" in events[0]
    chat_service.llama_stack_client.ask_stream.assert_not_called()


def test_reply_stream_uses_vector_store_context(
    chat_service, mock_llama_stack_client, mock_route_service
):
    mock_route_service.is_route_query.return_value = False
    list(
        chat_service.reply_stream(
            "Summarize supplier risk",
            chat_history=[],
            vector_store_id="vs_abc",
        )
    )
    mock_llama_stack_client.search_vector_store.assert_called_once_with(
        "vs_abc", "Summarize supplier risk", max_num_results=8
    )
    mock_llama_stack_client.ask_stream.assert_called_once()
    call_kw = mock_llama_stack_client.ask_stream.call_args.kwargs
    assert call_kw["context"] == "context chunk"


def test_reply_stream_llm_tokens_then_done(chat_service):
    events = list(chat_service.reply_stream("inventory levels?", chat_history=[]))
    assert events[0] == {"event": "start"}
    assert events[1] == {"event": "token", "delta": "Hello"}
    assert events[2] == {"event": "token", "delta": " world"}
    assert events[-1]["event"] == "done"
    assert events[-1]["answer"] == "Hello world"
    assert events[-1]["completion"] == {"model": "mock-model", "usage": None}


def test_latest_user_text_prefers_history():
    mock_llama = MagicMock()
    mock_route = MagicMock()
    mock_route.is_route_query.return_value = False
    svc = ChatService(mock_llama, mock_route, vector_store_client=None)
    history = [
        {"role": "human", "content": "first"},
        {"role": "ai", "content": "mid"},
        {"role": "human", "content": "  latest question  "},
    ]
    list(svc.reply_stream("ignored fallback", chat_history=history))
    mock_llama.ask_stream.assert_called_once()
    assert mock_llama.ask_stream.call_args.args[0] == "latest question"


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
    list(svc.reply_stream("query text", chat_history=[], vector_store_id=None))
    vs.similarity_search.assert_called_once_with("query text", k=3)
    ctx = mock_llama.ask_stream.call_args.kwargs["context"]
    assert ctx == "doc a"
