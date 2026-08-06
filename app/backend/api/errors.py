"""Domain exception hierarchy + Flask error-response mapping.

New/refactored internal code raises these instead of ad hoc
``{"success": False, ...}`` response dicts scattered across routes. Existing
route response shapes for currently-passing tests are intentionally left
untouched (the HTTP contract must not change) — this only cleans up how
*internal* code signals failure up to the route layer.
"""

from __future__ import annotations

from typing import Any

from flask import Flask, jsonify


class AppError(Exception):
    """Base class for domain errors that map to a JSON error response."""

    status_code = 500

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code

    def to_response_body(self) -> dict[str, Any]:
        return {"success": False, "error": self.message}


class ValidationError(AppError):
    """Caller-supplied input failed validation (HTTP 400)."""

    status_code = 400


class NotFoundError(AppError):
    """Requested resource does not exist (HTTP 404)."""

    status_code = 404


class UpstreamServiceError(AppError):
    """A downstream dependency (LlamaStack, General Simulation, PGVector) failed (HTTP 502)."""

    status_code = 502


def register_error_handlers(app: Flask) -> None:
    """Map ``AppError`` subclasses to JSON responses with the right status code."""

    @app.errorhandler(AppError)
    def _handle_app_error(exc: AppError):
        return jsonify(exc.to_response_body()), exc.status_code
