import logging
from typing import Any, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS

from clients.llama_stack_client import LlamaStackClient
from clients.vector_store_client import VectorStoreClient
from services.chat_service import ChatService
from services.dashboard_service import DashboardService
from services.knowledge_base_ingest_service import ingest_uploaded_files
from services.knowledge_bases_store import load_all as load_knowledge_bases
from services.route_service import RouteService
from services.simulations_store import append_simulation, load_all as load_simulations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

dashboard_service = DashboardService()

_vector_store_client: VectorStoreClient | None = None
try:
    _vector_store_client = VectorStoreClient()
    logger.info("VectorStoreClient initialised successfully.")
except Exception as _exc:
    logger.warning(
        "VectorStoreClient could not be initialised (%s). "
        "Chat will proceed without RAG context.",
        _exc,
    )

def list_vector_stores_safe(chat_service: Any) -> tuple[list[dict[str, Any]], Optional[str]]:
    """Return ``(stores, error_message)``. On failure, ``stores`` is empty and ``error_message`` is set."""
    try:
        return (chat_service.list_vector_stores(), None)
    except Exception as exc:
        logger.warning("list_vector_stores failed: %s", exc)
        return ([], str(exc))

chat_service = ChatService(
    LlamaStackClient(),
    RouteService(),
    vector_store_client=_vector_store_client,
)


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"ok": True})


@app.route("/api/v1/state", methods=["GET"])
def get_state():
    return jsonify(dashboard_service.get_state())


@app.route("/api/v1/trigger-event", methods=["POST"])
def trigger_event():
    payload = request.get_json(silent=True) or {}
    map_view = payload.get("mapView", "global")
    return jsonify(dashboard_service.trigger_event(map_view))


@app.route("/api/v1/simulate", methods=["POST"])
def post_simulate():
    payload = request.get_json(silent=True) or {}
    scenario = payload.get("scenario", "none")
    optimize = bool(payload.get("optimize", False))
    return jsonify(dashboard_service.simulate(scenario, optimize))


@app.route("/api/v1/chat", methods=["POST"])
def post_chat():
    payload = request.get_json(silent=True) or {}
    user_input = payload.get("input", "")
    chat_history = payload.get("chat_history") or []
    raw_vs = payload.get("vector_store_id") or payload.get("vectorStoreId") or ""
    vector_store_id = str(raw_vs).strip() or None
    return jsonify(
        chat_service.reply(
            user_input,
            chat_history=chat_history,
            vector_store_id=vector_store_id,
        )
    )

@app.route("/api/v1/knowledge-bases", methods=["GET"])
def get_knowledge_bases():
    """UI-upload catalog only. Merge with ``GET /api/v1/vector_stores`` in the client (same source as chat)."""
    return jsonify({"knowledge_bases": load_knowledge_bases()})


@app.route("/api/v1/knowledge-bases", methods=["POST"])
def post_knowledge_bases():
    """Multipart: ``name`` (text) + ``files`` (one or more uploads) → LlamaStack vector store."""
    name = (request.form.get("name") or "").strip()
    uploads = request.files.getlist("files")
    pairs: list[tuple[str, bytes]] = []
    for storage in uploads:
        if storage and storage.filename:
            pairs.append((storage.filename, storage.read()))
    result = ingest_uploaded_files(chat_service.llama_stack_client, name, pairs)
    if not result.get("ok"):
        return jsonify(result), 400
    return jsonify(result), 201


@app.route("/api/v1/vector_stores", methods=["GET"])
def get_vector_stores():
    """List LlamaStack vector stores (same listing the chat knowledge-base picker uses)."""
    try:
        stores, err = list_vector_stores_safe(chat_service)
        body: dict = {"vector_stores": stores}
        if err:
            body["error"] = err
        return jsonify(body)
    except Exception as exc:
        logger.warning("vector_stores.list failed: %s", exc)
        return jsonify({"vector_stores": [], "error": str(exc)}), 500


@app.route("/api/v1/simulations", methods=["GET"])
def get_simulations():
    return jsonify({"simulations": load_simulations()})


@app.route("/api/v1/simulations", methods=["POST"])
def post_simulation():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    description = payload.get("description", "")
    record = append_simulation(name, str(description))
    return jsonify({"simulation": record}), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True, threaded=True)
