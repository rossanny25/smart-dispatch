import json
from pathlib import Path
import sqlite3

from app.auth import DEFAULT_PASSWORD, DEFAULT_USERNAME
from app.main import create_app
from app.startup import prepare_runtime
from tests.asgi_client import request_asgi


def _app_and_database(tmp_path: Path):
    database_path = tmp_path / "users.db"
    prepare_runtime(database_path)
    return create_app(database_path=database_path), database_path


def _login_cookie(app: object, username: str, password: str) -> str:
    status, headers, _ = request_asgi(
        app,
        "/auth/login",
        method="POST",
        json_body={"username": username, "password": password},
        authenticated=False,
    )
    assert status == 200
    return headers["set-cookie"].split(";", 1)[0]


def _admin_headers(cookie: str, key: str) -> dict[str, str]:
    return {"cookie": cookie, "idempotency-key": key}


def test_startup_bootstraps_admin_user_without_plaintext_password(
    tmp_path: Path,
) -> None:
    _, database_path = _app_and_database(tmp_path)

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT username, role, password_hash, is_active
            FROM app_users
            WHERE username = ?
            """,
            (DEFAULT_USERNAME,),
        ).fetchone()

    assert row is not None
    assert row[0] == "admin"
    assert row[1] == "admin"
    assert row[2] != DEFAULT_PASSWORD
    assert row[2].startswith("pbkdf2_sha256$")
    assert row[3] == 1


def test_admin_can_list_create_and_edit_users(tmp_path: Path) -> None:
    app, _ = _app_and_database(tmp_path)
    admin_cookie = _login_cookie(app, DEFAULT_USERNAME, DEFAULT_PASSWORD)

    create_status, _, create_body = request_asgi(
        app,
        "/api/v1/admin/users",
        method="POST",
        json_body={
            "username": "tecnico-norte",
            "display_name": "Tecnico Norte",
            "role": "tecnico",
            "password": "tecnico2026",
        },
        headers=_admin_headers(admin_cookie, "create-tecnico-norte"),
        authenticated=False,
    )

    assert create_status == 201
    created = json.loads(create_body)["user"]
    assert created["username"] == "tecnico-norte"
    assert created["role"] == "tecnico"
    assert "password" not in created
    assert "password_hash" not in created

    update_status, _, update_body = request_asgi(
        app,
        f"/api/v1/admin/users/{created['id']}",
        method="PATCH",
        json_body={
            "display_name": "Tecnico Norte Senior",
            "role": "dispatcher",
            "is_active": False,
            "password": "nuevaClave2026",
        },
        headers=_admin_headers(admin_cookie, "update-tecnico-norte"),
        authenticated=False,
    )

    assert update_status == 200
    updated = json.loads(update_body)["user"]
    assert updated["display_name"] == "Tecnico Norte Senior"
    assert updated["role"] == "dispatcher"
    assert updated["is_active"] is False

    list_status, _, list_body = request_asgi(
        app,
        "/api/v1/admin/users",
        headers={"cookie": admin_cookie},
        authenticated=False,
    )

    assert list_status == 200
    users = json.loads(list_body)["users"]
    assert [user["username"] for user in users] == ["admin", "tecnico-norte"]


def test_admin_create_user_replays_same_idempotency_key(tmp_path: Path) -> None:
    app, _ = _app_and_database(tmp_path)
    admin_cookie = _login_cookie(app, DEFAULT_USERNAME, DEFAULT_PASSWORD)
    payload = {
        "username": "tecnico-idem",
        "display_name": "Tecnico Idem",
        "role": "tecnico",
        "password": "tecnico2026",
    }
    headers = _admin_headers(admin_cookie, "create-tecnico-idem")

    first_status, _, first_body = request_asgi(
        app,
        "/api/v1/admin/users",
        method="POST",
        json_body=payload,
        headers=headers,
        authenticated=False,
    )
    second_status, _, second_body = request_asgi(
        app,
        "/api/v1/admin/users",
        method="POST",
        json_body=payload,
        headers=headers,
        authenticated=False,
    )
    conflict_status, _, conflict_body = request_asgi(
        app,
        "/api/v1/admin/users",
        method="POST",
        json_body={**payload, "display_name": "Tecnico Cambiado"},
        headers=headers,
        authenticated=False,
    )

    assert first_status == 201
    assert second_status == 201
    assert json.loads(second_body) == json.loads(first_body)
    assert conflict_status == 409
    assert json.loads(conflict_body) == {"error": "idempotency_conflict"}


def test_admin_api_rejects_duplicate_username_and_invalid_role(tmp_path: Path) -> None:
    app, _ = _app_and_database(tmp_path)
    admin_cookie = _login_cookie(app, DEFAULT_USERNAME, DEFAULT_PASSWORD)
    payload = {
        "username": "tecnico-sur",
        "display_name": "Tecnico Sur",
        "role": "tecnico",
        "password": "tecnico2026",
    }

    assert request_asgi(
        app,
        "/api/v1/admin/users",
        method="POST",
        json_body=payload,
        headers=_admin_headers(admin_cookie, "create-tecnico-sur"),
        authenticated=False,
    )[0] == 201

    duplicate_status, _, duplicate_body = request_asgi(
        app,
        "/api/v1/admin/users",
        method="POST",
        json_body=payload,
        headers=_admin_headers(admin_cookie, "duplicate-tecnico-sur"),
        authenticated=False,
    )
    invalid_status, _, invalid_body = request_asgi(
        app,
        "/api/v1/admin/users",
        method="POST",
        json_body={**payload, "username": "externo", "role": "externo"},
        headers=_admin_headers(admin_cookie, "invalid-role"),
        authenticated=False,
    )

    assert duplicate_status == 409
    assert json.loads(duplicate_body)["error"] == "username_exists"
    assert invalid_status == 422
    assert json.loads(invalid_body)["error"] == "invalid_user"


def test_technician_cannot_use_admin_api(tmp_path: Path) -> None:
    app, _ = _app_and_database(tmp_path)
    admin_cookie = _login_cookie(app, DEFAULT_USERNAME, DEFAULT_PASSWORD)
    request_asgi(
        app,
        "/api/v1/admin/users",
        method="POST",
        json_body={
            "username": "tecnico-fisca",
            "display_name": "Tecnico Fisca",
            "role": "tecnico",
            "password": "smart2026AI",
        },
        headers=_admin_headers(admin_cookie, "create-tecnico-fisca"),
        authenticated=False,
    )
    technician_cookie = _login_cookie(app, "tecnico-fisca", "smart2026AI")

    status, _, body = request_asgi(
        app,
        "/api/v1/admin/users",
        headers={"cookie": technician_cookie},
        authenticated=False,
    )

    assert status == 403
    assert json.loads(body) == {"error": "admin_required"}


def test_cannot_disable_or_demote_last_active_admin(tmp_path: Path) -> None:
    app, _ = _app_and_database(tmp_path)
    admin_cookie = _login_cookie(app, DEFAULT_USERNAME, DEFAULT_PASSWORD)
    status, _, body = request_asgi(
        app,
        "/api/v1/admin/users",
        headers=_admin_headers(admin_cookie, "disable-last-admin"),
        authenticated=False,
    )
    assert status == 200
    admin_id = json.loads(body)["users"][0]["id"]

    disable_status, _, disable_body = request_asgi(
        app,
        f"/api/v1/admin/users/{admin_id}",
        method="PATCH",
        json_body={"is_active": False},
        headers=_admin_headers(admin_cookie, "disable-last-admin"),
        authenticated=False,
    )
    demote_status, _, demote_body = request_asgi(
        app,
        f"/api/v1/admin/users/{admin_id}",
        method="PATCH",
        json_body={"role": "tecnico"},
        headers=_admin_headers(admin_cookie, "demote-last-admin"),
        authenticated=False,
    )

    assert disable_status == 409
    assert json.loads(disable_body)["error"] == "last_admin_required"
    assert demote_status == 409
    assert json.loads(demote_body)["error"] == "last_admin_required"


def test_demoted_admin_cookie_loses_admin_access(tmp_path: Path) -> None:
    app, _ = _app_and_database(tmp_path)
    admin_cookie = _login_cookie(app, DEFAULT_USERNAME, DEFAULT_PASSWORD)
    request_asgi(
        app,
        "/api/v1/admin/users",
        method="POST",
        json_body={
            "username": "admin-dos",
            "display_name": "Admin Dos",
            "role": "admin",
            "password": "adminDos2026",
        },
        headers=_admin_headers(admin_cookie, "create-second-admin"),
        authenticated=False,
    )
    status, _, body = request_asgi(
        app,
        "/api/v1/admin/users",
        headers={"cookie": admin_cookie},
        authenticated=False,
    )
    admin_id = next(
        user["id"]
        for user in json.loads(body)["users"]
        if user["username"] == DEFAULT_USERNAME
    )
    assert status == 200

    demote_status, _, _ = request_asgi(
        app,
        f"/api/v1/admin/users/{admin_id}",
        method="PATCH",
        json_body={"role": "tecnico"},
        headers=_admin_headers(admin_cookie, "demote-first-admin"),
        authenticated=False,
    )
    denied_status, _, denied_body = request_asgi(
        app,
        "/api/v1/admin/users",
        headers={"cookie": admin_cookie},
        authenticated=False,
    )

    assert demote_status == 200
    assert denied_status == 401
    assert json.loads(denied_body) == {"error": "authentication_required"}


def test_update_requires_strict_boolean_for_active_state(tmp_path: Path) -> None:
    app, _ = _app_and_database(tmp_path)
    admin_cookie = _login_cookie(app, DEFAULT_USERNAME, DEFAULT_PASSWORD)
    status, _, body = request_asgi(
        app,
        "/api/v1/admin/users",
        headers={"cookie": admin_cookie},
        authenticated=False,
    )
    admin_id = json.loads(body)["users"][0]["id"]
    assert status == 200

    update_status, _, update_body = request_asgi(
        app,
        f"/api/v1/admin/users/{admin_id}",
        method="PATCH",
        json_body={"is_active": "false"},
        headers=_admin_headers(admin_cookie, "string-active-state"),
        authenticated=False,
    )

    assert update_status == 422
    assert json.loads(update_body)["error"]["code"] == "VALIDATION_FAILED"
