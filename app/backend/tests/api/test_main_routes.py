"""Flask ``main`` routes and ``list_vector_stores_safe``."""

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from werkzeug.datastructures import FileStorage


@pytest.fixture
def flask_client(monkeypatch, mock_llama_stack_client, mock_route_service):
    import main as app_main
    from services.chat_service import ChatService

    dash = MagicMock()
    dash.get_state.return_value = {"kpis": {}, "alerts": {}, "charts": {}, "mapData": {}}
    dash.trigger_event.return_value = {"after": "event"}
    dash.simulate.return_value = {"scenario": "done"}

    sim = MagicMock()
    sim.run_simulation.return_value = {
        "success": True,
        "answer": "Impact analysis complete.",
        "scenario_id": "opensky-uk-closure-001",
        "question": "What is affected?",
        "affected_entities": ["opensky-1"],
        "solver": {"impact_score": 0.5},
        "tool_call_trace": [],
    }
    sim.list_scenarios.return_value = {
        "success": True,
        "scenarios": ["opensky-uk-closure-001"],
    }
    sim.get_entities_geojson.return_value = {
        "success": True,
        "geojson": {"type": "FeatureCollection", "features": []},
    }

    chat = ChatService(mock_llama_stack_client, mock_route_service, vector_store_client=None)
    monkeypatch.setattr(app_main, "dashboard_service", dash)
    monkeypatch.setattr(app_main, "general_simulation_service", sim)
    monkeypatch.setattr(app_main, "chat_service", chat)
    app_main.app.config["TESTING"] = True
    return app_main.app.test_client(), app_main


def test_healthz(flask_client):
    client, _ = flask_client
    rv = client.get("/healthz")
    assert rv.status_code == 200
    assert rv.get_json() == {"ok": True}


def test_get_state(flask_client):
    client, app_main = flask_client
    rv = client.get("/api/v1/state")
    assert rv.status_code == 200
    assert rv.get_json() == app_main.dashboard_service.get_state.return_value


def test_post_chat(flask_client, mock_llama_stack_client):
    client, _ = flask_client
    rv = client.post("/api/v1/chat", json={"input": "inventory levels?"})
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["answer"] == "mocked answer"
    mock_llama_stack_client.ask.assert_called()


def test_post_chat_stream(flask_client, mock_llama_stack_client):
    client, _ = flask_client
    rv = client.post("/api/v1/chat", json={"input": "inventory levels?", "stream": True})
    assert rv.status_code == 200
    assert rv.content_type.startswith("text/event-stream")
    body = rv.get_data(as_text=True)
    assert '"type": "delta"' in body
    assert '"type": "done"' in body
    assert '"answer": "mocked answer"' in body
    mock_llama_stack_client.ask_stream.assert_called()
    mock_llama_stack_client.ask.assert_not_called()


def test_post_simulate(flask_client):
    client, _ = flask_client
    rv = client.post("/api/v1/simulate", json={"scenario": "none", "optimize": False})
    assert rv.status_code == 200
    assert rv.get_json()["scenario"] == "done"


def test_simulations_post_validation(flask_client, tmp_path, monkeypatch):
    monkeypatch.setenv("SIMULATIONS_STORE_PATH", str(tmp_path / "sim.json"))
    client, _ = flask_client
    bad = client.post("/api/v1/simulations", json={})
    assert bad.status_code == 400
    ok = client.post("/api/v1/simulations", json={"name": "Run A", "description": "x"})
    assert ok.status_code == 201


def test_get_vector_stores(flask_client, mock_llama_stack_client):
    client, _ = flask_client
    rv = client.get("/api/v1/vector_stores")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "vector_stores" in data
    assert len(data["vector_stores"]) == 1


def test_get_vector_stores_handles_list_error(flask_client, mock_llama_stack_client):
    client, _ = flask_client
    mock_llama_stack_client.list_vector_stores.side_effect = RuntimeError("nope")
    rv = client.get("/api/v1/vector_stores")
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["vector_stores"] == []
    assert "error" in body


@patch("main.ingest_uploaded_files")
def test_post_knowledge_bases_multipart(mock_ingest, flask_client):
    mock_ingest.return_value = {"ok": True, "knowledge_base": {"id": "kb1", "name": "N"}}
    client, _ = flask_client
    data = {
        "name": "Docs",
        "files": FileStorage(
            stream=BytesIO(b"hello"),
            filename="note.txt",
            content_type="text/plain",
        ),
    }
    rv = client.post("/api/v1/knowledge-bases", data=data, content_type="multipart/form-data")
    assert rv.status_code == 201
    mock_ingest.assert_called_once()


def test_get_knowledge_bases_uses_env_store(tmp_path, monkeypatch, flask_client):
    path = tmp_path / "kb.json"
    monkeypatch.setenv("KNOWLEDGE_BASES_STORE_PATH", str(path))
    import services.knowledge_bases_store as kb

    kb.append_record({"id": "1", "name": "Local", "vector_store_id": "vs", "files": []})
    client, _ = flask_client
    rv = client.get("/api/v1/knowledge-bases")
    assert rv.status_code == 200
    names = [x["name"] for x in rv.get_json()["knowledge_bases"]]
    assert "Local" in names


def test_list_vector_stores_safe_success():
    import main as app_main

    cs = MagicMock()
    cs.list_vector_stores.return_value = [{"id": "a"}]
    stores, err = app_main.list_vector_stores_safe(cs)
    assert stores == [{"id": "a"}]
    assert err is None


def test_list_vector_stores_safe_on_exception():
    import main as app_main

    cs = MagicMock()
    cs.list_vector_stores.side_effect = ValueError("bad")
    stores, err = app_main.list_vector_stores_safe(cs)
    assert stores == []
    assert "bad" in err


def test_post_general_simulation_query(flask_client):
    client, app_main = flask_client
    rv = client.post(
        "/api/v1/general-simulation/query",
        json={"question": "What is affected?", "scenario_id": "opensky-uk-closure-001"},
    )
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["success"] is True
    assert body["answer"] == "Impact analysis complete."
    app_main.general_simulation_service.run_simulation.assert_called_once_with(
        "What is affected?",
        "opensky-uk-closure-001",
    )


def test_post_general_simulation_query_validation_error(flask_client):
    client, app_main = flask_client
    app_main.general_simulation_service.run_simulation.return_value = {
        "success": False,
        "error": "question is required",
    }
    rv = client.post("/api/v1/general-simulation/query", json={"scenario_id": "s1"})
    assert rv.status_code == 400
    assert rv.get_json()["error"] == "question is required"


def test_get_general_simulation_scenarios(flask_client):
    client, app_main = flask_client
    rv = client.get("/api/v1/general-simulation/scenarios")
    assert rv.status_code == 200
    assert rv.get_json()["scenarios"] == ["opensky-uk-closure-001"]
    app_main.general_simulation_service.list_scenarios.assert_called_once_with()


def test_get_general_simulation_scenarios_upstream_error(flask_client):
    client, app_main = flask_client
    app_main.general_simulation_service.list_scenarios.return_value = {
        "success": False,
        "error": "unreachable",
        "scenarios": [],
    }
    rv = client.get("/api/v1/general-simulation/scenarios")
    assert rv.status_code == 502


def test_get_general_simulation_entities_geojson(flask_client):
    client, app_main = flask_client
    rv = client.get(
        "/api/v1/general-simulation/entities/geojson",
        query_string={"bbox": "-15,35,40,62", "ids": "a,b", "limit": "10"},
    )
    assert rv.status_code == 200
    assert rv.get_json()["geojson"]["type"] == "FeatureCollection"
    app_main.general_simulation_service.get_entities_geojson.assert_called_once_with(
        bbox="-15,35,40,62",
        ids=["a", "b"],
        limit=10,
    )


def test_get_general_simulation_entities_geojson_bad_limit(flask_client):
    client, _ = flask_client
    rv = client.get(
        "/api/v1/general-simulation/entities/geojson",
        query_string={"limit": "nope"},
    )
    assert rv.status_code == 400
    assert "limit" in rv.get_json()["error"]
