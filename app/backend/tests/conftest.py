"""Shared fixtures for backend tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def reset_supply_chain_event_slot():
    """Clear the module-level simulated event TTL slot between tests."""
    import services.supply_chain_state_builder as mod

    mod._event_slot["event"] = None
    mod._event_slot["timestamp"] = 0.0
    yield
    mod._event_slot["event"] = None
    mod._event_slot["timestamp"] = 0.0


@pytest.fixture
def mock_llama_stack_client():
    def _ask_stream(*_args, **_kwargs):
        yield {"type": "delta", "content": "mocked "}
        yield {"type": "delta", "content": "answer"}
        yield {"type": "done", "answer": "mocked answer", "completion": None}

    def _ask_stream_with_tools(*_args, **_kwargs):
        yield {"type": "delta", "content": "mocked "}
        yield {"type": "delta", "content": "answer"}
        yield {
            "type": "done",
            "answer": "mocked answer",
            "completion": None,
            "tool_calls_made": [],
        }

    client = MagicMock()
    client.ask.return_value = {"answer": "mocked answer", "completion": None}
    client.ask_with_tools.return_value = {
        "answer": "mocked answer",
        "completion": None,
        "tool_calls_made": [],
    }
    client.ask_stream.side_effect = _ask_stream
    client.ask_stream_with_tools.side_effect = _ask_stream_with_tools
    client.list_vector_stores.return_value = [
        {"id": "vs_1", "name": "Demo KB", "status": "ready", "created_at": 0}
    ]
    client.search_vector_store.return_value = "context chunk"
    client.create_vector_store.return_value = "vs_new"
    client.upload_file_bytes.return_value = "file_1"
    client.attach_file_to_vector_store.return_value = None
    client.delete_vector_store.return_value = None
    return client


@pytest.fixture
def mock_route_service():
    svc = MagicMock()
    svc.is_route_query.return_value = False
    svc.get_optimized_route.return_value = {
        "answer": "route",
        "routeData": {"type": "optimized_land_route", "coordinates": [], "color": "#000"},
    }
    return svc
