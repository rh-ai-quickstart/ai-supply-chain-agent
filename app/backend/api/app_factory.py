"""Flask application factory (Dependency Inversion composition point).

``create_app`` builds (or accepts) a ``Container``, registers per-domain
blueprints against it, and wires CORS + the domain-error handler. Route
paths, methods, and JSON response shapes are unchanged from the previous
monolithic ``main.py`` — only the internal wiring moved.
"""

from __future__ import annotations

from container import Container
from errors import register_error_handlers
from flask import Flask
from flask_cors import CORS
from routes import chat as chat_routes
from routes import dashboard as dashboard_routes
from routes import general_simulation as general_simulation_routes
from routes import health as health_routes
from routes import knowledge_bases as knowledge_bases_routes
from routes import news as news_routes
from routes import scenarios as scenarios_routes
from routes import simulations as simulations_routes
from settings import Settings


def create_app(settings: Settings | None = None, container: Container | None = None) -> Flask:
    """Build the Flask app. Pass an explicit ``container`` in tests to inject fakes."""
    settings = settings or Settings.from_env()
    container = container or Container(settings)

    app = Flask(__name__)
    app.container = container  # type: ignore[attr-defined]

    # Same-origin through nginx — CORS not required in production.
    # In development, Vite proxies /api to the backend (same origin).
    # Set Settings.cors_origin (env var CORS_ORIGIN) if running the frontend separately.
    if settings.cors_origin:
        CORS(app, origins=settings.cors_origin)

    register_error_handlers(app)

    for module in (
        health_routes,
        dashboard_routes,
        news_routes,
        chat_routes,
        knowledge_bases_routes,
        simulations_routes,
        scenarios_routes,
        general_simulation_routes,
    ):
        app.register_blueprint(module.create_blueprint(container))

    return app
