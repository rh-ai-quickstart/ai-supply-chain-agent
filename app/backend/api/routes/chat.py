"""Chat (sync + SSE streaming) and vector-store listing routes."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from container import Container
from flask import Blueprint, Response, jsonify, request, stream_with_context

logger = logging.getLogger(__name__)


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


def list_vector_stores_safe(chat_service: Any) -> tuple[list[dict[str, Any]], Optional[str]]:
    """Return ``(stores, error_message)``. On failure, ``stores`` is empty and ``error_message`` is set."""
    try:
        return (chat_service.list_vector_stores(), None)
    # Broad catch: this wrapper is intended to report any failure instead of raising.
    except Exception as exc:
        logger.warning("list_vector_stores failed: %s", exc)
        return ([], str(exc))


def create_blueprint(container: Container) -> Blueprint:
    bp = Blueprint("chat", __name__)

    @bp.route("/api/v1/chat", methods=["POST"])
    def post_chat():
        args = _parse_chat_payload(request.get_json(silent=True) or {})
        chat_service = container.chat_service

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

    @bp.route("/api/v1/vector_stores", methods=["GET"])
    def get_vector_stores():
        """List LlamaStack vector stores (same listing the chat knowledge-base picker uses)."""
        try:
            stores, err = list_vector_stores_safe(container.chat_service)
            body: dict = {"vector_stores": stores}
            if err:
                body["error"] = err
            return jsonify(body)
        # Broad catch: top-level HTTP boundary; return a 500 for any unexpected handler error.
        except Exception as exc:
            logger.warning("vector_stores.list failed: %s", exc)
            return jsonify({"vector_stores": [], "error": str(exc)}), 500

    return bp
