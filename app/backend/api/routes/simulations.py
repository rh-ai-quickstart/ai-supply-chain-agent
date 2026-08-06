"""Demo "simulations" catalog routes."""

from __future__ import annotations

from container import Container
from flask import Blueprint, jsonify, request


def create_blueprint(container: Container) -> Blueprint:
    bp = Blueprint("simulations", __name__)

    @bp.route("/api/v1/simulations", methods=["GET"])
    def get_simulations():
        return jsonify({"simulations": container.simulation_repository.load_all()})

    @bp.route("/api/v1/simulations", methods=["POST"])
    def post_simulation():
        payload = request.get_json(silent=True) or {}
        name = (payload.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name is required"}), 400
        description = payload.get("description", "")
        record = container.simulation_repository.append_simulation(name, str(description))
        return jsonify({"simulation": record}), 201

    return bp
