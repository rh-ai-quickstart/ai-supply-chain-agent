"""General-simulation scenario propose/create routes (LLM-drafted overlays)."""

from __future__ import annotations

from container import Container
from flask import Blueprint, jsonify, request


def create_blueprint(container: Container) -> Blueprint:
    bp = Blueprint("scenarios", __name__)

    @bp.route("/api/v1/scenarios/propose", methods=["POST"])
    def post_scenarios_propose():
        """LLM draft for a new general-simulation overlay (name, id, bbox, description)."""
        payload = request.get_json(silent=True) or {}
        prompt = payload.get("prompt") or payload.get("description") or ""
        result = container.scenario_create_service.propose(str(prompt))
        status = 200 if result.get("success") else 400
        return jsonify(result), status

    @bp.route("/api/v1/scenarios", methods=["POST"])
    def post_scenarios_create():
        """Persist a confirmed draft into general-simulation (Neo4j + PostGIS bbox sync)."""
        payload = request.get_json(silent=True) or {}
        draft = payload.get("draft") if isinstance(payload.get("draft"), dict) else payload
        result = container.scenario_create_service.create(draft if isinstance(draft, dict) else {})
        status = 201 if result.get("success") else 400
        return jsonify(result), status

    return bp
