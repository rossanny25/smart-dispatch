import json
from pathlib import Path
import sqlite3

from app.auth import DEFAULT_PASSWORD, DEFAULT_USERNAME, ensure_default_admin_user
from app.main import create_app
from app.startup import prepare_runtime
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


def test_oversized_login_payload_is_rejected() -> None:
    app = create_app()

    status, _, body = request_asgi(
        app,
        "/auth/login",
        method="POST",
        body=b'{"username":"' + (b"a" * 17_000) + b'","password":"x"}',
        headers={"content-type": "application/json"},
        authenticated=False,
    )

    assert status == 413
    assert json.loads(body) == {"error": "payload_too_large"}


def test_valid_json_login_sets_session_cookie_and_unlocks_api(tmp_path: Path) -> None:
    database_path = tmp_path / "auth.db"
    prepare_runtime(database_path)
    app = create_app(database_path=database_path)

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
        "role": "admin",
        "display_name": "Administrador",
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


def test_logout_clears_session_cookie(tmp_path: Path) -> None:
    database_path = tmp_path / "auth.db"
    prepare_runtime(database_path)
    app = create_app(database_path=database_path)
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


def test_forgot_password_reports_manual_recovery() -> None:
    app = create_app()

    status, _, body = request_asgi(
        app,
        "/auth/forgot-password",
        method="POST",
        json_body={"username": DEFAULT_USERNAME},
        authenticated=False,
    )

    assert status == 200
    assert json.loads(body)["status"] == "manual_recovery_required"


def test_login_does_not_fallback_when_user_store_is_corrupt(tmp_path: Path) -> None:
    database_path = tmp_path / "corrupt.db"
    database_path.write_text("not sqlite", encoding="utf-8")
    app = create_app(database_path=database_path)

    status, _, body = request_asgi(
        app,
        "/auth/login",
        method="POST",
        json_body={"username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD},
        authenticated=False,
    )

    assert status == 401
    assert json.loads(body) == {"error": "invalid_credentials"}


def test_bootstrap_repairs_inactive_or_demoted_configured_admin(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "auth.db"
    prepare_runtime(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE app_users
            SET role = 'tecnico', is_active = 0, password_hash = ?
            WHERE username = ?
            """,
            ("pbkdf2_sha256$210000$bad$bad", DEFAULT_USERNAME),
        )

    ensure_default_admin_user(database_path)
    app = create_app(database_path=database_path)
    status, _, body = request_asgi(
        app,
        "/auth/login",
        method="POST",
        json_body={"username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD},
        authenticated=False,
    )

    assert status == 200
    assert json.loads(body)["role"] == "admin"


def test_malformed_password_hash_rejects_login_without_crashing(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "auth.db"
    prepare_runtime(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "UPDATE app_users SET password_hash = ? WHERE username = ?",
            ("pbkdf2_sha256$999999999$not-base64$also-bad", DEFAULT_USERNAME),
        )
    app = create_app(database_path=database_path)

    status, _, body = request_asgi(
        app,
        "/auth/login",
        method="POST",
        json_body={"username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD},
        authenticated=False,
    )

    assert status == 401
    assert json.loads(body) == {"error": "invalid_credentials"}
