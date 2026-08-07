from time import time

import pytest
from flask import Flask, jsonify, make_response
from flask_limiter import Limiter, RequestLimit
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import HTTPException


def test_unknown_route_returns_404(client):
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Resource not found"}


def test_wrong_method_returns_405(client):
    response = client.get("/auth/login")

    assert response.status_code == 405


def test_malformed_json_returns_400_not_500(client):
    response = client.post(
        "/auth/login", data="{broken", content_type="application/json"
    )

    assert response.status_code == 400


def test_oversized_body_returns_413_not_500(client):
    response = client.post(
        "/auth/login",
        data=b"x" * (6 * 1024 * 1024),
        content_type="application/json",
    )

    assert response.status_code == 413


def test_missing_token_returns_401(client):
    response = client.get("/users/me")

    assert response.status_code == 401


@pytest.fixture
def limited_app():
    """A minimal app wired like main.py, so the handler chain can be exercised."""

    def on_breach(rate_limit: RequestLimit):
        reset_in_seconds = rate_limit.reset_at - time()
        return make_response(
            jsonify(
                {
                    "error": f"Rate limit exceeded and will reset in {reset_in_seconds:.0f} seconds."
                }
            ),
            429,
        )

    app = Flask("limited")
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri="memory://",
        on_breach=on_breach,
        enabled=True,
    )
    limiter.init_app(app)

    @app.errorhandler(HTTPException)
    def http_error_handler(error):
        if error.response is not None:
            return error.response
        return jsonify({"error": error.description}), error.code

    @app.errorhandler(Exception)
    def internal_error_handler(error):
        return jsonify({"error": "An unexpected error occurred"}), 500

    @app.route("/limited")
    @limiter.limit("1 per hour")
    def limited():
        return jsonify({"ok": True}), 200

    return app


def test_rate_limit_breach_returns_429_with_its_own_body(limited_app):
    client = limited_app.test_client()

    assert client.get("/limited").status_code == 200

    breached = client.get("/limited")

    assert breached.status_code == 429
    assert "Rate limit exceeded" in breached.get_json()["error"]
