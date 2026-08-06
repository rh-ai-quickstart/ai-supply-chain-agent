"""``/healthz`` (liveness), ``/readyz`` (readiness), and ``/api/v1/version``.

``/api/v1/version`` reports the git commit + build time baked into the
container image at build time (see the Containerfile ``ARG``s and the
Makefile's ``build-backend`` target), so an operator can confirm a running
pod is actually serving the code they expect.
"""

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

    @bp.route("/api/v1/version", methods=["GET"])
    def version():
        return jsonify(
            {
                "git_commit": container.settings.git_commit,
                "build_time": container.settings.build_time,
            }
        )

    return bp
