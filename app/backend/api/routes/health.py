"""``/healthz`` (liveness) and ``/readyz`` (downstream-dependency readiness)."""

from __future__ import annotations

from container import Container
from flask import Blueprint, jsonify


def create_blueprint(container: Container) -> Blueprint:
    bp = Blueprint("health", __name__)

    @bp.route("/healthz", methods=["GET"])
    def healthz():
        return jsonify({"ok": True})

    @bp.route("/readyz", methods=["GET"])
    def readyz():
        result = container.readiness_service.check()
        status = 200 if result["ready"] else 503
        return jsonify(result), status

    return bp
