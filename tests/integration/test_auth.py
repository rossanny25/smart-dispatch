import json

from app.auth import DEFAULT_PASSWORD, DEFAULT_USERNAME
from app.main import create_app
from tests.asgi_client import request_asgi


def test_browser_without_session_is_redirected_to_login() -> None:
    app = create_app()

    status, headers, _ = request_asgi(app, "/", authenticated=False)

    assert status == 303
    assert headers["location"] == "/login"


def test_api_without_session_returns_authentication_error() -> None:
    app = create_app()

    status, _, body = request_asgi(app, "/api/orders", authenticated=False)

    assert status == 401
    assert json.loads(body) == {"error": "authentication_required"}


def test_login_page_is_public() -> None:
    app = create_app()

    status, headers, body = request_asgi(app, "/login", authenticated=False)

    assert status == 200
    assert headers["content-type"].startswith("text/html")
    assert b"Acceso operativo" in body


def test_invalid_json_login_is_rejected() -> None:
    app = create_app()

    status, _, body = request_asgi(
        app,
        "/auth/login",
        method="POST",
        json_body={"username": DEFAULT_USERNAME, "password": "incorrecta"},
        authenticated=False,
    )

    assert status == 401
    assert json.loads(body) == {"error": "invalid_credentials"}


def test_valid_json_login_sets_session_cookie_and_unlocks_api() -> None:
    app = create_app()

    status, headers, body = request_asgi(
        app,
        "/auth/login",
        method="POST",
        json_body={"username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD},
        authenticated=False,
    )

    assert status == 200
    assert json.loads(body) == {
        "authenticated": True,
        "username": DEFAULT_USERNAME,
    }
    cookie = headers["set-cookie"].split(";", 1)[0]

    api_status, _, api_body = request_asgi(
        app,
        "/api/orders",
        headers={"cookie": cookie},
        authenticated=False,
    )

    assert api_status == 200
    assert isinstance(json.loads(api_body), list)


def test_logout_clears_session_cookie() -> None:
    app = create_app()
    _, headers, _ = request_asgi(
        app,
        "/auth/login",
        method="POST",
        json_body={"username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD},
        authenticated=False,
    )
    cookie = headers["set-cookie"].split(";", 1)[0]

    status, logout_headers, body = request_asgi(
        app,
        "/auth/logout",
        method="POST",
        headers={"cookie": cookie},
        authenticated=False,
    )

    assert status == 200
    assert json.loads(body) == {"authenticated": False}
    assert "smart_dispatch_session=" in logout_headers["set-cookie"]
