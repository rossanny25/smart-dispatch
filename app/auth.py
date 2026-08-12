from __future__ import annotations

import base64
import hmac
import json
import os
import time
from hashlib import sha256
from typing import Any
from urllib.parse import parse_qs

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse, Response


SESSION_COOKIE = "smart_dispatch_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
DEFAULT_USERNAME = "tecnico-fisca"
DEFAULT_PASSWORD = "smart2026AI"


def configured_username() -> str:
    return os.environ.get("SMART_DISPATCH_LOGIN_USER", DEFAULT_USERNAME)


def configured_password() -> str:
    return os.environ.get("SMART_DISPATCH_LOGIN_PASSWORD", DEFAULT_PASSWORD)


def session_secret() -> str:
    return os.environ.get(
        "SMART_DISPATCH_SESSION_SECRET",
        "smart-dispatch-local-session-secret-change-me",
    )


def _sign(payload: str) -> str:
    return hmac.new(
        session_secret().encode("utf-8"),
        payload.encode("utf-8"),
        sha256,
    ).hexdigest()


def create_session_token(username: str, now: int | None = None) -> str:
    issued_at = int(time.time() if now is None else now)
    expires_at = issued_at + SESSION_TTL_SECONDS
    payload = f"{username}:{expires_at}"
    raw = f"{payload}:{_sign(payload)}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def verify_session_token(token: str | None, now: int | None = None) -> bool:
    if not token:
        return False
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        username, expires_at_text, signature = raw.rsplit(":", 2)
        expires_at = int(expires_at_text)
    except (ValueError, UnicodeDecodeError):
        return False

    payload = f"{username}:{expires_at}"
    expected_signature = _sign(payload)
    current_time = int(time.time() if now is None else now)
    return (
        hmac.compare_digest(username, configured_username())
        and hmac.compare_digest(signature, expected_signature)
        and expires_at > current_time
    )


def request_is_authenticated(request: Request) -> bool:
    return verify_session_token(request.cookies.get(SESSION_COOKIE))


def attach_session_cookie(response: Response, username: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(username),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax")


async def read_login_credentials(request: Request) -> tuple[str, str]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            payload: Any = await request.json()
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        return str(payload.get("username", "")), str(payload.get("password", ""))

    body = (await request.body()).decode("utf-8")
    form = parse_qs(body)
    username = form.get("username", [""])[0]
    password = form.get("password", [""])[0]
    return username, password


def credentials_are_valid(username: str, password: str) -> bool:
    return hmac.compare_digest(username, configured_username()) and hmac.compare_digest(
        password,
        configured_password(),
    )


def unauthenticated_response(request: Request) -> Response:
    accept = request.headers.get("accept", "")
    if request.url.path.startswith("/api") or "application/json" in accept:
        return JSONResponse({"error": "authentication_required"}, status_code=401)
    return RedirectResponse("/login", status_code=303)
