"""Domain exception hierarchy + Flask error-handler wiring."""

from flask import Flask

from errors import AppError, NotFoundError, UpstreamServiceError, ValidationError, register_error_handlers


def _make_app() -> Flask:
    app = Flask(__name__)
    register_error_handlers(app)

    @app.route("/boom-validation")
    def boom_validation():
        raise ValidationError("bad input")

    @app.route("/boom-not-found")
    def boom_not_found():
        raise NotFoundError("missing")

    @app.route("/boom-upstream")
    def boom_upstream():
        raise UpstreamServiceError("upstream down")

    @app.route("/boom-custom")
    def boom_custom():
        raise AppError("custom", status_code=418)

    return app


def test_validation_error_maps_to_400():
    client = _make_app().test_client()
    rv = client.get("/boom-validation")
    assert rv.status_code == 400
    assert rv.get_json() == {"success": False, "error": "bad input"}


def test_not_found_error_maps_to_404():
    client = _make_app().test_client()
    rv = client.get("/boom-not-found")
    assert rv.status_code == 404
    assert rv.get_json()["error"] == "missing"


def test_upstream_service_error_maps_to_502():
    client = _make_app().test_client()
    rv = client.get("/boom-upstream")
    assert rv.status_code == 502
    assert rv.get_json()["error"] == "upstream down"


def test_app_error_supports_custom_status_code():
    client = _make_app().test_client()
    rv = client.get("/boom-custom")
    assert rv.status_code == 418
