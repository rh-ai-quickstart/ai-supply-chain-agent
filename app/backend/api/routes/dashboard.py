"""Dashboard state, simulate, and trigger-event routes."""

from __future__ import annotations

from container import Container
from flask import Blueprint, jsonify, request


def create_blueprint(container: Container) -> Blueprint:
    bp = Blueprint("dashboard", __name__)

    @bp.route("/api/v1/state", methods=["GET"])
    def get_state():
        return jsonify(container.dashboard_service.get_state())

    @bp.route("/api/v1/trigger-event", methods=["POST"])
    def trigger_event():
        payload = request.get_json(silent=True) or {}
        map_view = payload.get("mapView", "global")
        return jsonify(container.dashboard_service.trigger_event(map_view))

    @bp.route("/api/v1/simulate", methods=["POST"])
    def post_simulate():
        payload = request.get_json(silent=True) or {}
        scenario = payload.get("scenario", "none")
        optimize = payload.get("optimize", False) in (True, "true", "1", 1)
        return jsonify(container.dashboard_service.simulate(scenario, optimize))

    return bp
