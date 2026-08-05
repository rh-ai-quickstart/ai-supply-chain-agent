import json
import logging
import os
from typing import Any, Optional

from clients.llama_stack_client import LlamaStackClient
from clients.vector_store_client import VectorStoreClient
from flask import Flask, Response, jsonify, request, stream_with_context
from flask_cors import CORS
from services.chat_service import ChatService
from services.dashboard_service import DashboardService
from services.general_simulation_service import GeneralSimulationService
from services.knowledge_base_ingest_service import ingest_uploaded_files
from services.knowledge_bases_store import load_all as load_knowledge_bases
from services.news_service import NewsService
from services.route_service import RouteService
from services.simulations_store import append_simulation
from services.simulations_store import load_all as load_simulations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Same-origin through nginx — CORS not required in production.
# In development, Vite proxies /api to the backend (same origin).
# Set CORS_ORIGIN env var if running the frontend separately.
_cors_origin = os.getenv("CORS_ORIGIN")
if _cors_origin:
    CORS(app, origins=_cors_origin)

dashboard_service = DashboardService()
general_simulation_service = GeneralSimulationService()
news_service = NewsService()

_vector_store_client: VectorStoreClient | None = None
try:
    _vector_store_client = VectorStoreClient()
    logger.info("VectorStoreClient initialised successfully.")
# Broad catch: best-effort init; external libs may raise varied errors, proceed without RAG context.
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
    # Broad catch: this wrapper is intended to report any failure instead of raising.
    except Exception as exc:
        logger.warning("list_vector_stores failed: %s", exc)
        return ([], str(exc))

_openai_model = os.getenv("LLAMA_STACK_OPENAI_MODEL", "")
if not _openai_model:
    logger.error(
        "LLAMA_STACK_OPENAI_MODEL is not set. Set it to the model ID for the OpenAI-compatible endpoint."
    )
    _openai_model = "gpt-4o-mini"

_llama_stack_url = (os.getenv("LLAMA_STACK_URL") or "").rstrip("/")
# Local OpenAI-only setups often point LLAMA_STACK_URL at api.openai.com. The default
# Llama Stack model ID is invalid there, so use the OpenAI model for the primary client.
_stack_is_openai = "api.openai.com" in _llama_stack_url
if _stack_is_openai:
    logger.warning(
        "LLAMA_STACK_URL points at OpenAI (%s); using model %s for the primary chat client "
        "instead of LLAMA_STACK_MODEL.",
        _llama_stack_url,
        _openai_model,
    )
    _primary_client = LlamaStackClient(model=_openai_model, label="vllm")
else:
    _primary_client = LlamaStackClient(label="vllm")

chat_service = ChatService(
    _primary_client,
    RouteService(),
    vector_store_client=_vector_store_client,
    openai_client=LlamaStackClient(model=_openai_model, label="openai"),
)


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"ok": True})


@app.route("/api/v1/state", methods=["GET"])
def get_state():
    return jsonify(dashboard_service.get_state())


@app.route("/api/v1/news", methods=["GET"])
def get_news():
    limit_raw = request.args.get("limit")
    limit = 30
    if limit_raw is not None and str(limit_raw).strip() != "":
        try:
            limit = int(limit_raw)
        except (TypeError, ValueError):
            return jsonify({"error": "limit must be an integer"}), 400
    return jsonify(news_service.get_headlines(limit=limit))


@app.route("/api/v1/trigger-event", methods=["POST"])
def trigger_event():
    payload = request.get_json(silent=True) or {}
    map_view = payload.get("mapView", "global")
    return jsonify(dashboard_service.trigger_event(map_view))


@app.route("/api/v1/simulate", methods=["POST"])
def post_simulate():
    payload = request.get_json(silent=True) or {}
    scenario = payload.get("scenario", "none")
    optimize = payload.get("optimize", False) in (True, "true", "1", 1)
    return jsonify(dashboard_service.simulate(scenario, optimize))


def _sse_event(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False)
    text = text.replace("\n\n", "\n")
    return f"data: {text}\n\n"


def _parse_chat_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_vs = payload.get("vector_store_id") or payload.get("vectorStoreId") or ""
    raw_scenario = payload.get("scenario_id") or payload.get("scenarioId") or ""
    return {
        "user_input": payload.get("input", ""),
        "chat_history": payload.get("chat_history") or [],
        "vector_store_id": str(raw_vs).strip() or None,
        "scenario_id": str(raw_scenario).strip() or None,
        "use_vllm": bool(payload.get("use_vllm", True)),
        "stream": bool(payload.get("stream", False)),
    }


@app.route("/api/v1/chat", methods=["POST"])
def post_chat():
    args = _parse_chat_payload(request.get_json(silent=True) or {})

    if args["stream"]:
        def generate():
            for event in chat_service.reply_stream(
                args["user_input"],
                chat_history=args["chat_history"],
                vector_store_id=args["vector_store_id"],
                use_vllm=args["use_vllm"],
                scenario_id=args["scenario_id"],
            ):
                yield _sse_event(event)

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    return jsonify(
        chat_service.reply(
            args["user_input"],
            chat_history=args["chat_history"],
            vector_store_id=args["vector_store_id"],
            use_vllm=args["use_vllm"],
            scenario_id=args["scenario_id"],
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
    # Broad catch: top-level HTTP boundary; return a 500 for any unexpected handler error.
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


@app.route("/api/v1/general-simulation/query", methods=["POST"])
def post_general_simulation_query():
    payload = request.get_json(silent=True) or {}
    question = payload.get("question", "")
    scenario_id = payload.get("scenario_id") or payload.get("scenarioId") or ""
    result = general_simulation_service.run_simulation(question, scenario_id)
    status = 200 if result.get("success") else 400
    return jsonify(result), status


@app.route("/api/v1/general-simulation/scenarios", methods=["GET"])
def get_general_simulation_scenarios():
    result = general_simulation_service.list_scenarios()
    status = 200 if result.get("success") else 502
    return jsonify(result), status


@app.route("/api/v1/general-simulation/entities/geojson", methods=["GET"])
def get_general_simulation_entities_geojson():
    bbox = request.args.get("bbox") or None
    ids_raw = request.args.get("ids") or ""
    ids = [part.strip() for part in ids_raw.split(",") if part.strip()] or None
    limit_raw = request.args.get("limit")
    limit = None
    if limit_raw is not None and str(limit_raw).strip() != "":
        try:
            limit = int(limit_raw)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "limit must be an integer"}), 400
    result = general_simulation_service.get_entities_geojson(
        bbox=bbox,
        ids=ids,
        limit=limit,
    )
    status = 200 if result.get("success") else 502
    return jsonify(result), status


if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(host="0.0.0.0", port=5001, debug=debug, threaded=True)
