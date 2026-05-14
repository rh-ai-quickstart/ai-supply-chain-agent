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
def knowledge_bases_store_module(tmp_path, monkeypatch):
    """Point the knowledge-base JSON catalog at a temp file (per test)."""
    path = tmp_path / "knowledge_bases.json"
    monkeypatch.setenv("KNOWLEDGE_BASES_STORE_PATH", str(path))
    import services.knowledge_bases_store as kb

    return kb


@pytest.fixture
def simulations_store_module(tmp_path, monkeypatch):
    """Point the simulations JSON store at a temp file (per test)."""
    path = tmp_path / "simulations.json"
    monkeypatch.setenv("SIMULATIONS_STORE_PATH", str(path))
    import services.simulations_store as sim

    return sim


@pytest.fixture
def mock_llama_stack_client():
    client = MagicMock()
    client.ask.return_value = {"answer": "mocked answer", "completion": None}
    client.list_vector_stores.return_value = [
        {"id": "vs_1", "name": "Demo KB", "status": "ready", "created_at": 0}
    ]
    client.search_vector_store.return_value = "context chunk"
    client.create_vector_store.return_value = "vs_new"
    client.upload_file_bytes.return_value = "file_1"
    client.attach_file_to_vector_store.return_value = None
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
