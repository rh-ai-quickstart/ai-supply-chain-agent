"""Tests for ``services.general_simulation_service``."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.general_simulation_service import GeneralSimulationService


def _make_mock_client() -> MagicMock:
    client = MagicMock()
    client.health.return_value = {"status": "healthy"}
    client.query.return_value = {
        "answer": "The port strike delays shipments by 3 days.",
        "scenario_id": "port-strike",
        "question": "What is the impact?",
        "affected_entities": ["PORT001", "PORT002"],
        "solver": {"impact_score": 0.6},
        "tool_call_trace": [],
    }
    client.list_scenarios.return_value = {
        "scenarios": ["opensky-uk-closure-001", "port-strike"],
    }
    client.get_entities_geojson.return_value = {
        "type": "FeatureCollection",
        "features": [],
    }
    return client


class TestGeneralSimulationServiceCheckHealth:
    def test_health_delegates_to_client(self):
        client = _make_mock_client()
        service = GeneralSimulationService(client)
        result = service.check_health()
        assert result == {"status": "healthy"}
        client.health.assert_called_once()

    def test_health_delegates_via_default_client(self):
        """When no client is injected, the default client's health is returned."""
        client = _make_mock_client()
        service = GeneralSimulationService.__new__(GeneralSimulationService)
        service._client = client  # bypass __init__ to avoid real requests
        result = service.check_health()
        assert result == {"status": "healthy"}


class TestGeneralSimulationServiceRunSimulation:
    def test_success_propagates_answer(self):
        client = _make_mock_client()
        service = GeneralSimulationService(client)
        result = service.run_simulation("What is the impact?", "port-strike")
        assert result["success"] is True
        assert result["answer"] == "The port strike delays shipments by 3 days."
        assert result["scenario_id"] == "port-strike"
        assert result["question"] == "What is the impact?"
        assert result["affected_entities"] == ["PORT001", "PORT002"]
        assert result["solver"] == {"impact_score": 0.6}
        assert result["tool_call_trace"] == []
        client.query.assert_called_once_with("What is the impact?", "port-strike")

    def test_success_uses_defaults_when_keys_missing_from_client(self):
        client = MagicMock()
        client.query.return_value = {}
        service = GeneralSimulationService(client)
        result = service.run_simulation("hi", "s1")
        assert result["success"] is True
        assert result["answer"] == ""
        assert result["scenario_id"] == "s1"
        assert result["question"] == "hi"
        assert result["affected_entities"] == []
        assert result["solver"] == {}
        assert result["tool_call_trace"] == []

    def test_empty_question_returns_error(self):
        client = _make_mock_client()
        service = GeneralSimulationService(client)
        result = service.run_simulation("", "s1")
        assert result["success"] is False
        assert result["error"] == "question is required"
        client.query.assert_not_called()

    def test_whitespace_only_question_returns_error(self):
        client = _make_mock_client()
        service = GeneralSimulationService(client)
        result = service.run_simulation("   \t\n", "s1")
        assert result["success"] is False
        assert result["error"] == "question is required"
        client.query.assert_not_called()

    def test_empty_scenario_id_returns_error(self):
        client = _make_mock_client()
        service = GeneralSimulationService(client)
        result = service.run_simulation("question", "")
        assert result["success"] is False
        assert result["error"] == "scenario_id is required"
        client.query.assert_not_called()

    def test_whitespace_only_scenario_id_returns_error(self):
        client = _make_mock_client()
        service = GeneralSimulationService(client)
        result = service.run_simulation("question", "  \t\n")
        assert result["success"] is False
        assert result["error"] == "scenario_id is required"
        client.query.assert_not_called()

    def test_client_error_is_propagated(self):
        client = _make_mock_client()
        client.query.return_value = {"error": "Service unavailable"}
        service = GeneralSimulationService(client)
        result = service.run_simulation("ok", "s1")
        assert result["success"] is False
        assert result["error"] == "Service unavailable"

    def test_question_and_scenario_are_stripped_before_call(self):
        client = _make_mock_client()
        service = GeneralSimulationService(client)
        service.run_simulation("  hi  ", "  s1  ")
        client.query.assert_called_once_with("hi", "s1")


class TestGeneralSimulationServiceListScenarios:
    def test_success(self):
        client = _make_mock_client()
        service = GeneralSimulationService(client)
        result = service.list_scenarios()
        assert result["success"] is True
        assert result["scenarios"] == ["opensky-uk-closure-001", "port-strike"]
        client.list_scenarios.assert_called_once_with()

    def test_client_error(self):
        client = _make_mock_client()
        client.list_scenarios.return_value = {"error": "unreachable"}
        service = GeneralSimulationService(client)
        result = service.list_scenarios()
        assert result["success"] is False
        assert result["error"] == "unreachable"
        assert result["scenarios"] == []


class TestGeneralSimulationServiceGetEntitiesGeojson:
    def test_success(self):
        client = _make_mock_client()
        service = GeneralSimulationService(client)
        result = service.get_entities_geojson(
            bbox="-15,35,40,62",
            ids=["e1"],
            limit=10,
        )
        assert result["success"] is True
        assert result["geojson"]["type"] == "FeatureCollection"
        client.get_entities_geojson.assert_called_once_with(
            bbox="-15,35,40,62",
            ids=["e1"],
            limit=10,
        )

    def test_client_error(self):
        client = _make_mock_client()
        client.get_entities_geojson.return_value = {"error": "timeout"}
        service = GeneralSimulationService(client)
        result = service.get_entities_geojson()
        assert result["success"] is False
        assert result["error"] == "timeout"
