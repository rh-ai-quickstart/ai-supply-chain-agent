import logging

from flask import Flask, jsonify, request
from flask_cors import CORS

from clients.llama_stack_client import LlamaStackClient
from clients.vector_store_client import VectorStoreClient
from services.chat_service import ChatService
from services.dashboard_service import DashboardService
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
    return jsonify(chat_service.reply(user_input))


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
