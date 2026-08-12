import asyncio
from pathlib import Path
import subprocess
import sys
from typing import Mapping

import pytest

from app.auth import DEFAULT_USERNAME, SESSION_COOKIE, create_session_token


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def request_asgi(
    app: object,
    path: str,
    *,
    request_headers: Mapping[str, str] | None = None,
    authenticated: bool = True,
) -> tuple[int, dict[str, str], bytes]:
    messages: list[dict[str, object]] = []
    request_sent = False

    async def receive() -> dict[str, object]:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    headers = dict(request_headers or {})
    has_cookie = any(key.lower() == "cookie" for key in headers)
    if authenticated and not has_cookie:
        headers["cookie"] = f"{SESSION_COOKIE}={create_session_token(DEFAULT_USERNAME)}"

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [
            (key.lower().encode(), value.encode())
            for key, value in headers.items()
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8000),
    }
    asyncio.run(app(scope, receive, send))  # type: ignore[operator]

    start = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")  # type: ignore[arg-type]
        for message in messages
        if message["type"] == "http.response.body"
    )
    headers = {
        key.decode().lower(): value.decode()
        for key, value in start["headers"]  # type: ignore[index]
    }
    return int(start["status"]), headers, body  # type: ignore[arg-type]


def test_importing_app_main_has_no_runtime_side_effects(tmp_path: Path) -> None:
    db_path = tmp_path / "must-not-exist.db"
    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=tmp_path,
        env={
            "PATH": "",
            "PYTHONPATH": str(PROJECT_ROOT),
            "SMART_DISPATCH_DB_PATH": str(db_path),
        },
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert not db_path.exists()


def test_root_and_local_static_files_are_served() -> None:
    from app.main import app

    responses = {
        "/": request_asgi(app, "/"),
        "/index.css": request_asgi(app, "/index.css"),
        "/main.js": request_asgi(app, "/main.js"),
    }

    assert all(response[0] == 200 for response in responses.values())
    assert b"Smart Dispatch" in responses["/"][2]
    assert responses["/index.css"][1]["content-type"].startswith("text/css")
    assert "javascript" in responses["/main.js"][1]["content-type"]
    cors_status, cors_headers, _ = request_asgi(
        app,
        "/",
        request_headers={"Origin": "https://untrusted.example"},
    )
    assert cors_status == 200
    assert "access-control-allow-origin" not in cors_headers


def test_runtime_prepares_before_starting_uvicorn(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.runtime as runtime

    events: list[object] = []
    monkeypatch.delenv("SMART_DISPATCH_HOST", raising=False)
    monkeypatch.delenv("SMART_DISPATCH_PORT", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    monkeypatch.setattr(runtime, "prepare_runtime", lambda: events.append("prepared"))
    monkeypatch.setattr(
        runtime.uvicorn,
        "run",
        lambda *args, **kwargs: events.append(("uvicorn", args, kwargs)),
    )

    runtime.main()

    assert events == [
        "prepared",
        (
            "uvicorn",
            ("app.main:app",),
            {"host": "127.0.0.1", "port": 8000, "workers": 1},
        ),
    ]


def test_runtime_accepts_platform_port_when_specific_port_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.runtime as runtime

    events: list[object] = []
    monkeypatch.setenv("SMART_DISPATCH_HOST", "0.0.0.0")
    monkeypatch.delenv("SMART_DISPATCH_PORT", raising=False)
    monkeypatch.setenv("PORT", "7860")
    monkeypatch.setattr(runtime, "prepare_runtime", lambda: events.append("prepared"))
    monkeypatch.setattr(
        runtime.uvicorn,
        "run",
        lambda *args, **kwargs: events.append(("uvicorn", args, kwargs)),
    )

    runtime.main()

    assert events == [
        "prepared",
        (
            "uvicorn",
            ("app.main:app",),
            {"host": "0.0.0.0", "port": 7860, "workers": 1},
        ),
    ]


def test_runtime_allows_explicit_container_host_and_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.runtime as runtime

    events: list[object] = []
    monkeypatch.setenv("SMART_DISPATCH_HOST", "0.0.0.0")
    monkeypatch.setenv("SMART_DISPATCH_PORT", "8050")
    monkeypatch.setattr(runtime, "prepare_runtime", lambda: events.append("prepared"))
    monkeypatch.setattr(
        runtime.uvicorn,
        "run",
        lambda *args, **kwargs: events.append(("uvicorn", args, kwargs)),
    )

    runtime.main()

    assert events == [
        "prepared",
        (
            "uvicorn",
            ("app.main:app",),
            {"host": "0.0.0.0", "port": 8050, "workers": 1},
        ),
    ]


def test_runtime_never_starts_uvicorn_when_preparation_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.runtime as runtime

    started = False

    def fail_preparation() -> None:
        raise runtime.StartupError("migration failed")

    def mark_started(*args: object, **kwargs: object) -> None:
        nonlocal started
        started = True

    monkeypatch.setattr(runtime, "prepare_runtime", fail_preparation)
    monkeypatch.setattr(runtime.uvicorn, "run", mark_started)

    with pytest.raises(SystemExit) as exc:
        runtime.main()

    assert exc.value.code == 1
    assert not started
