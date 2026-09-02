"""``GeneralSimulationClient`` HTTP error/timeout shapes with a mocked session."""

from unittest.mock import MagicMock

import requests
from clients.general_simulation_client import GeneralSimulationClient


def _json_response(payload, status=200):
    response = MagicMock()
    response.status_code = status
    response.json.return_value = payload
    response.text = str(payload)
    response.raise_for_status = MagicMock()
    if status >= 400:
        http_error = requests.HTTPError(response=response)
        response.raise_for_status.side_effect = http_error
    return response


def test_health_returns_payload_on_success():
    session = MagicMock()
    session.get.return_value = _json_response({"status": "ok", "db": "up"})
    client = GeneralSimulationClient(base_url="http://gen-sim:8000", session=session)
    assert client.health() == {"status": "ok", "db": "up"}
    session.get.assert_called_once_with("http://gen-sim:8000/health", timeout=10)


def test_health_unreachable_on_network_error():
    session = MagicMock()
    session.get.side_effect = requests.ConnectionError("down")
    client = GeneralSimulationClient(session=session)
    assert client.health() == {"status": "unreachable", "db": "unknown"}


def test_query_success():
    session = MagicMock()
    session.post.return_value = _json_response({"answer": "ok", "affected_entities": []})
    client = GeneralSimulationClient(base_url="http://gs", timeout=5, session=session)
    out = client.query("Which flights?", "opensky-uk-closure-001")
    assert out["answer"] == "ok"
    session.post.assert_called_once()
    assert session.post.call_args.kwargs["json"] == {
        "question": "Which flights?",
        "scenario_id": "opensky-uk-closure-001",
    }


def test_query_timeout():
    session = MagicMock()
    session.post.side_effect = requests.Timeout()
    client = GeneralSimulationClient(timeout=12, session=session)
    assert client.query("q", "s1") == {"error": "Request timed out after 12s"}


def test_query_http_error():
    session = MagicMock()
    bad = _json_response({"detail": "nope"}, status=502)
    session.post.return_value = bad
    client = GeneralSimulationClient(session=session)
    out = client.query("q", "s1")
    assert out["error"].startswith("HTTP 502:")


def test_list_scenarios_list_payload():
    session = MagicMock()
    session.get.return_value = _json_response(["opensky-uk-closure-001", "port-strike"])
    client = GeneralSimulationClient(session=session)
    assert client.list_scenarios() == {
        "scenarios": ["opensky-uk-closure-001", "port-strike"],
    }


def test_list_scenarios_unexpected_shape():
    session = MagicMock()
    session.get.return_value = _json_response({"unexpected": True})
    client = GeneralSimulationClient(session=session)
    assert client.list_scenarios() == {"error": "Unexpected scenarios response shape"}


def test_get_entities_geojson_passes_params():
    session = MagicMock()
    session.get.return_value = _json_response(
        {"type": "FeatureCollection", "features": []}
    )
    client = GeneralSimulationClient(session=session)
    out = client.get_entities_geojson(bbox="-1,2,3,4", ids=["a", "b"], limit=10)
    assert out["type"] == "FeatureCollection"
    assert session.get.call_args.kwargs["params"] == {
        "bbox": "-1,2,3,4",
        "ids": "a,b",
        "limit": 10,
    }


def test_sync_spatial_requires_scenario_id():
    client = GeneralSimulationClient(session=MagicMock())
    assert client.sync_spatial("  ") == {"error": "scenario_id is required"}


def test_sync_spatial_success():
    session = MagicMock()
    session.post.return_value = _json_response(
        {"status": "synced", "scenario_id": "s1", "total_affected": 3}
    )
    client = GeneralSimulationClient(base_url="http://gs", session=session)
    out = client.sync_spatial("s1")
    assert out["status"] == "synced"
    session.post.assert_called_once_with(
        "http://gs/admin/graph/scenarios/s1/sync-spatial",
        timeout=120,
    )


def test_sync_spatial_timeout():
    session = MagicMock()
    session.post.side_effect = requests.Timeout()
    client = GeneralSimulationClient(timeout=30, session=session)
    assert client.sync_spatial("s1") == {"error": "Request timed out after 30s"}


def test_create_event_success():
    session = MagicMock()
    session.post.return_value = _json_response(
        {"status": "injected", "event_id": "evt-1", "affected_count": 2}
    )
    client = GeneralSimulationClient(base_url="http://gs", session=session)
    out = client.create_event(
        event_id="evt-1",
        scenario_id="s1",
        description="Runway closure",
        bbox="-1,50,1,52",
        attributes={"severity": "high"},
    )
    assert out["event_id"] == "evt-1"
    payload = session.post.call_args.kwargs["json"]
    assert payload["bbox"] == "-1,50,1,52"
    assert payload["attributes"] == {"severity": "high"}


def test_create_event_http_error():
    session = MagicMock()
    session.post.return_value = _json_response({"detail": "bad bbox"}, status=400)
    client = GeneralSimulationClient(session=session)
    out = client.create_event(
        event_id="e",
        scenario_id="s",
        description="d",
        bbox="bad",
    )
    assert out["error"].startswith("HTTP 400:")


def test_create_event_timeout():
    session = MagicMock()
    session.post.side_effect = requests.Timeout()
    client = GeneralSimulationClient(timeout=5, session=session)
    out = client.create_event(
        event_id="e",
        scenario_id="s",
        description="d",
        bbox="-1,50,1,52",
    )
    assert out["error"] == "Request timed out after 5s"


def test_list_scenarios_timeout():
    session = MagicMock()
    session.get.side_effect = requests.Timeout()
    client = GeneralSimulationClient(session=session)
    assert client.list_scenarios() == {"error": "Request timed out after 30s"}


def test_get_entities_geojson_timeout():
    session = MagicMock()
    session.get.side_effect = requests.Timeout()
    client = GeneralSimulationClient(session=session)
    assert client.get_entities_geojson() == {"error": "Request timed out after 60s"}


def test_get_entities_geojson_unexpected_shape():
    session = MagicMock()
    session.get.return_value = _json_response(["not", "a", "dict"])
    client = GeneralSimulationClient(session=session)
    assert client.get_entities_geojson() == {"error": "Unexpected geojson response shape"}
