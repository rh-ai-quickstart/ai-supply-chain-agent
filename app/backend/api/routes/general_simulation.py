"""General-simulation query/scenarios/entities-geojson proxy routes."""

from __future__ import annotations

from container import Container
from flask import Blueprint, jsonify, request


def create_blueprint(container: Container) -> Blueprint:
    bp = Blueprint("general_simulation", __name__)

    @bp.route("/api/v1/general-simulation/query", methods=["POST"])
    def post_general_simulation_query():
        payload = request.get_json(silent=True) or {}
        question = payload.get("question", "")
        scenario_id = payload.get("scenario_id") or payload.get("scenarioId") or ""
        result = container.general_simulation_service.run_simulation(question, scenario_id)
        status = 200 if result.get("success") else 400
        return jsonify(result), status

    @bp.route("/api/v1/general-simulation/scenarios", methods=["GET"])
    def get_general_simulation_scenarios():
        result = container.general_simulation_service.list_scenarios()
        status = 200 if result.get("success") else 502
        return jsonify(result), status

    @bp.route("/api/v1/general-simulation/entities/geojson", methods=["GET"])
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
        result = container.general_simulation_service.get_entities_geojson(
            bbox=bbox,
            ids=ids,
            limit=limit,
        )
        status = 200 if result.get("success") else 502
        return jsonify(result), status

    return bp
