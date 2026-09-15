from container import Container
from flask import Blueprint, jsonify, request


def create_blueprint(container: Container) -> Blueprint:
    bp = Blueprint("kpis", __name__)

    @bp.route("/api/v1/kpis", methods=["GET"])
    def get_kpis():
        scenario_id = request.args.get("scenario_id") or request.args.get("scenarioId") or ""
        bbox = request.args.get("bbox")
        result = container.kpi_service.get_kpis(
            scenario_id=scenario_id or None,
            bbox=bbox,
        )
        status = 200 if result.get("success") else 502
        return jsonify(result), status

    @bp.route("/api/v1/kpis", methods=["POST"])
    def post_kpis():
        payload = request.get_json(silent=True) or {}
        scenario_id = payload.get("scenario_id") or payload.get("scenarioId") or ""
        bbox = payload.get("bbox")
        solver = payload.get("solver")
        affected_entities = payload.get("affected_entities") or payload.get("affectedEntities")
        if affected_entities is not None and not isinstance(affected_entities, list):
            return jsonify({"success": False, "error": "affected_entities must be an array"}), 400

        result = container.kpi_service.compute_kpis(
            scenario_id=scenario_id or None,
            bbox=bbox,
            solver=solver if isinstance(solver, dict) else None,
            affected_entities=affected_entities,
        )
        status = 200 if result.get("success") else 502
        return jsonify(result), status

    return bp
