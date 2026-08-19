from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import hmac
import json
import os
import sqlite3
import time
from typing import Any
from urllib.parse import parse_qs
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.adapters.persistence.database import connect_sqlite, resolve_database_path


SESSION_COOKIE = "smart_dispatch_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "smart2026AI"
DEFAULT_DISPLAY_NAME = "Administrador"
ALLOWED_ROLES = {"admin", "tecnico", "dispatcher"}
PASSWORD_ITERATIONS = 210_000
MAX_LOGIN_BODY_BYTES = 16_384


@dataclass(frozen=True)
class UserAccount:
    id: str
    username: str
    display_name: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class UserSession:
    user_id: str
    username: str
    role: str
    expires_at: int


class AuthStoreUnavailable(RuntimeError):
    """The SQLite user store is not ready yet."""


class DuplicateUsernameError(ValueError):
    """A requested username already exists."""


class InvalidUserInputError(ValueError):
    """User-management payload failed validation."""


class LastAdminError(ValueError):
    """The last active admin cannot be demoted or disabled."""


class UserNotFoundError(LookupError):
    """The requested user does not exist."""


class LoginPayloadTooLarge(ValueError):
    """Login request body exceeded the accepted size."""


def configured_username() -> str:
    return os.environ.get("SMART_DISPATCH_LOGIN_USER", DEFAULT_USERNAME)


def configured_password() -> str:
    return os.environ.get("SMART_DISPATCH_LOGIN_PASSWORD", DEFAULT_PASSWORD)


def session_secret() -> str:
    return os.environ.get(
        "SMART_DISPATCH_SESSION_SECRET",
        "smart-dispatch-local-session-secret-change-me",
    )


def session_cookie_secure() -> bool:
    return os.environ.get("SMART_DISPATCH_COOKIE_SECURE", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def utc_now_text() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _connect(database_path: str | os.PathLike[str] | None = None) -> sqlite3.Connection:
    connection = connect_sqlite(resolve_database_path(database_path))
    connection.row_factory = sqlite3.Row
    return connection


def _table_exists(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = 'app_users'"
    ).fetchone()
    return row is not None


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    selected_salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        selected_salt,
        PASSWORD_ITERATIONS,
    )
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS,
        base64.urlsafe_b64encode(selected_salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        if iterations <= 0 or iterations > PASSWORD_ITERATIONS:
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
    except (ValueError, UnicodeDecodeError, binascii.Error):
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual, expected)


def _sign(payload: str) -> str:
    return hmac.new(
        session_secret().encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_session_token(
    username: str,
    now: int | None = None,
    *,
    user_id: str = "",
    role: str = "admin",
) -> str:
    issued_at = int(time.time() if now is None else now)
    expires_at = issued_at + SESSION_TTL_SECONDS
    payload_data = {
        "uid": user_id,
        "u": username,
        "r": role,
        "exp": expires_at,
    }
    payload = json.dumps(payload_data, separators=(",", ":"), sort_keys=True)
    raw = f"{payload}:{_sign(payload)}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def create_session_token_for_user(
    user: UserAccount,
    now: int | None = None,
) -> str:
    return create_session_token(
        user.username,
        now,
        user_id=user.id,
        role=user.role,
    )


def read_session_token(token: str | None, now: int | None = None) -> UserSession | None:
    if not token:
        return None
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        payload, signature = raw.rsplit(":", 1)
        data: Any = json.loads(payload)
        expires_at = int(data["exp"])
        username = str(data["u"])
        role = str(data["r"])
        user_id = str(data.get("uid", ""))
    except (ValueError, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return None

    current_time = int(time.time() if now is None else now)
    if expires_at <= current_time:
        return None
    if role not in ALLOWED_ROLES:
        return None
    if not hmac.compare_digest(signature, _sign(payload)):
        return None
    return UserSession(
        user_id=user_id,
        username=username,
        role=role,
        expires_at=expires_at,
    )


def verify_session_token(token: str | None, now: int | None = None) -> bool:
    return read_session_token(token, now) is not None


def current_session(
    request: Request,
    database_path: str | os.PathLike[str] | None = None,
) -> UserSession | None:
    session = read_session_token(request.cookies.get(SESSION_COOKIE))
    if session is None or database_path is None:
        return session
    return _revalidate_session(session, database_path)


def request_is_authenticated(
    request: Request,
    database_path: str | os.PathLike[str] | None = None,
) -> bool:
    return current_session(request, database_path) is not None


def request_is_admin(
    request: Request,
    database_path: str | os.PathLike[str] | None = None,
) -> bool:
    session = current_session(request, database_path)
    return session is not None and session.role == "admin"


def attach_session_cookie(response: Response, username: str, role: str = "admin") -> None:
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(username, role=role),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=session_cookie_secure(),
        samesite="lax",
    )


def attach_session_cookie_for_user(response: Response, user: UserAccount) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token_for_user(user),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=session_cookie_secure(),
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax")


async def _read_limited_body(request: Request) -> bytes:
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_LOGIN_BODY_BYTES:
            raise LoginPayloadTooLarge("login payload is too large")
        body.extend(chunk)
    return bytes(body)


async def read_login_credentials(request: Request) -> tuple[str, str]:
    content_type = request.headers.get("content-type", "")
    body = await _read_limited_body(request)
    if "application/json" in content_type:
        try:
            payload: Any = json.loads(body.decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        return str(payload.get("username", "")), str(payload.get("password", ""))

    form = parse_qs(body.decode("utf-8", errors="replace"))
    username = form.get("username", [""])[0]
    password = form.get("password", [""])[0]
    return username, password


def request_hash(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_idempotency_record(
    *,
    route: str,
    idempotency_key: str,
    request_hash_value: str,
    database_path: str | os.PathLike[str] | None = None,
) -> tuple[int, dict[str, object]] | str | None:
    with _connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT request_hash, response_status, response_body_json
            FROM idempotency_records
            WHERE route = ? AND idempotency_key = ?
            """,
            (route, idempotency_key),
        ).fetchone()
    if row is None:
        return None
    if str(row["request_hash"]) != request_hash_value:
        return "conflict"
    try:
        body = json.loads(str(row["response_body_json"]))
    except json.JSONDecodeError:
        body = {"error": "idempotency_record_corrupt"}
    if not isinstance(body, dict):
        body = {"value": body}
    return int(row["response_status"]), body


def store_idempotency_record(
    *,
    route: str,
    idempotency_key: str,
    request_hash_value: str,
    response_status: int,
    response_body: dict[str, object],
    database_path: str | os.PathLike[str] | None = None,
) -> None:
    with _connect(database_path) as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO idempotency_records (
                route, idempotency_key, request_hash, response_status,
                response_body_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                route,
                idempotency_key,
                request_hash_value,
                response_status,
                json.dumps(response_body, ensure_ascii=False, sort_keys=True),
                utc_now_text(),
            ),
        )


def _row_to_user(row: sqlite3.Row) -> UserAccount:
    return UserAccount(
        id=str(row["id"]),
        username=str(row["username"]),
        display_name=str(row["display_name"]),
        role=str(row["role"]),
        is_active=bool(row["is_active"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def serialize_user(user: UserAccount) -> dict[str, object]:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


def ensure_default_admin_user(database_path: str | os.PathLike[str] | None = None) -> None:
    with _connect(database_path) as connection:
        if not _table_exists(connection):
            raise AuthStoreUnavailable("app_users table is not available.")
        existing = connection.execute(
            "SELECT * FROM app_users WHERE username = ?",
            (configured_username(),),
        ).fetchone()
        if (
            existing is not None
            and str(existing["role"]) == "admin"
            and bool(existing["is_active"])
        ):
            return
        now = utc_now_text()
        if existing is None:
            connection.execute(
                """
                INSERT INTO app_users (
                    id, username, display_name, role, password_hash, is_active,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, 'admin', ?, 1, ?, ?)
                """,
                (
                    str(uuid4()),
                    configured_username(),
                    DEFAULT_DISPLAY_NAME,
                    hash_password(configured_password()),
                    now,
                    now,
                ),
            )
            return
        connection.execute(
            """
            UPDATE app_users
            SET display_name = ?, role = 'admin', password_hash = ?,
                is_active = 1, updated_at = ?
            WHERE id = ?
            """,
            (
                str(existing["display_name"] or DEFAULT_DISPLAY_NAME),
                hash_password(configured_password()),
                now,
                str(existing["id"]),
            ),
        )


def authenticate_user(
    username: str,
    password: str,
    database_path: str | os.PathLike[str] | None = None,
) -> UserAccount | None:
    try:
        with _connect(database_path) as connection:
            if not _table_exists(connection):
                return _fallback_user(username, password)
            row = connection.execute(
                """
                SELECT * FROM app_users
                WHERE username = ? AND is_active = 1
                """,
                (username,),
            ).fetchone()
    except sqlite3.DatabaseError:
        return None

    if row is None:
        return None
    if not verify_password(password, str(row["password_hash"])):
        return None
    return _row_to_user(row)


def _fallback_user(username: str, password: str) -> UserAccount | None:
    if not (
        hmac.compare_digest(username, configured_username())
        and hmac.compare_digest(password, configured_password())
    ):
        return None
    now = utc_now_text()
    return UserAccount(
        id="fallback-admin",
        username=configured_username(),
        display_name=DEFAULT_DISPLAY_NAME,
        role="admin",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def credentials_are_valid(
    username: str,
    password: str,
    database_path: str | os.PathLike[str] | None = None,
) -> bool:
    return authenticate_user(username, password, database_path) is not None


def list_users(database_path: str | os.PathLike[str] | None = None) -> list[UserAccount]:
    with _connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM app_users
            ORDER BY role = 'admin' DESC, username ASC
            """
        ).fetchall()
    return [_row_to_user(row) for row in rows]


def create_user(
    *,
    username: str,
    display_name: str,
    role: str,
    password: str,
    database_path: str | os.PathLike[str] | None = None,
) -> UserAccount:
    normalized_username = _validate_username(username)
    normalized_name = _validate_display_name(display_name)
    normalized_role = _validate_role(role)
    _validate_password(password)
    now = utc_now_text()
    user_id = str(uuid4())
    try:
        with _connect(database_path) as connection:
            connection.execute(
                """
                INSERT INTO app_users (
                    id, username, display_name, role, password_hash, is_active,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    user_id,
                    normalized_username,
                    normalized_name,
                    normalized_role,
                    hash_password(password),
                    now,
                    now,
                ),
            )
            row = connection.execute(
                "SELECT * FROM app_users WHERE id = ?",
                (user_id,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        raise DuplicateUsernameError("username already exists") from error
    if row is None:
        raise UserNotFoundError("user was not persisted")
    return _row_to_user(row)


def update_user(
    user_id: str,
    *,
    display_name: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
    password: str | None = None,
    database_path: str | os.PathLike[str] | None = None,
) -> UserAccount:
    updates: list[str] = []
    values: list[object] = []
    if display_name is not None:
        updates.append("display_name = ?")
        values.append(_validate_display_name(display_name))
    if role is not None:
        updates.append("role = ?")
        values.append(_validate_role(role))
    if is_active is not None:
        updates.append("is_active = ?")
        values.append(1 if is_active else 0)
    if password:
        _validate_password(password)
        updates.append("password_hash = ?")
        values.append(hash_password(password))

    with _connect(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        current = connection.execute(
            "SELECT * FROM app_users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if current is None:
            raise UserNotFoundError("user does not exist")
        target_role = role if role is not None else str(current["role"])
        target_active = bool(is_active) if is_active is not None else bool(current["is_active"])
        if str(current["role"]) == "admin" and (
            target_role != "admin" or not target_active
        ):
            active_admins = connection.execute(
                """
                SELECT count(*) FROM app_users
                WHERE role = 'admin' AND is_active = 1
                """
            ).fetchone()[0]
            if active_admins <= 1:
                raise LastAdminError("cannot modify the last active admin")

        if updates:
            updates.append("updated_at = ?")
            values.append(utc_now_text())
            values.append(user_id)
            connection.execute(
                f"UPDATE app_users SET {', '.join(updates)} WHERE id = ?",
                values,
            )
        row = connection.execute(
            "SELECT * FROM app_users WHERE id = ?",
            (user_id,),
        ).fetchone()
    if row is None:
        raise UserNotFoundError("user does not exist")
    return _row_to_user(row)


def _revalidate_session(
    session: UserSession,
    database_path: str | os.PathLike[str],
) -> UserSession | None:
    try:
        with _connect(database_path) as connection:
            if not _table_exists(connection):
                return session
            if session.user_id:
                row = connection.execute(
                    "SELECT * FROM app_users WHERE id = ?",
                    (session.user_id,),
                ).fetchone()
            else:
                row = connection.execute(
                    "SELECT * FROM app_users WHERE username = ?",
                    (session.username,),
                ).fetchone()
    except sqlite3.DatabaseError:
        return None

    if row is None or not bool(row["is_active"]):
        return None
    if str(row["username"]) != session.username or str(row["role"]) != session.role:
        return None
    return session


def _validate_username(username: str) -> str:
    normalized = username.strip().lower()
    if len(normalized) < 3 or len(normalized) > 80:
        raise InvalidUserInputError("username must be between 3 and 80 characters")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
    if any(character not in allowed for character in normalized):
        raise InvalidUserInputError("username has invalid characters")
    return normalized


def _validate_display_name(display_name: str) -> str:
    normalized = display_name.strip()
    if not normalized or len(normalized) > 120:
        raise InvalidUserInputError("display name must be between 1 and 120 characters")
    return normalized


def _validate_role(role: str) -> str:
    normalized = role.strip().lower()
    if normalized not in ALLOWED_ROLES:
        raise InvalidUserInputError("role is invalid")
    return normalized


def _validate_password(password: str) -> None:
    if len(password) < 8 or len(password) > 256:
        raise InvalidUserInputError("password must be between 8 and 256 characters")


def unauthenticated_response(request: Request) -> Response:
    accept = request.headers.get("accept", "")
    if request.url.path.startswith("/api") or "application/json" in accept:
        return JSONResponse({"error": "authentication_required"}, status_code=401)
    return RedirectResponse("/login", status_code=303)
