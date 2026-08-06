"""News headlines route."""

from __future__ import annotations

from container import Container
from flask import Blueprint, jsonify, request


def create_blueprint(container: Container) -> Blueprint:
    bp = Blueprint("news", __name__)

    @bp.route("/api/v1/news", methods=["GET"])
    def get_news():
        limit_raw = request.args.get("limit")
        limit = 30
        if limit_raw is not None and str(limit_raw).strip() != "":
            try:
                limit = int(limit_raw)
            except (TypeError, ValueError):
                return jsonify({"error": "limit must be an integer"}), 400
        return jsonify(container.news_service.get_headlines(limit=limit))

    return bp
