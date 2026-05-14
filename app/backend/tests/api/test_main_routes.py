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

    chat = ChatService(mock_llama_stack_client, mock_route_service, vector_store_client=None)
    monkeypatch.setattr(app_main, "dashboard_service", dash)
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
