"""Canonical fail-closed runtime launcher."""

import os
import sys
from collections.abc import Callable

import uvicorn

from app.startup import StartupError, prepare_runtime


HOST = "127.0.0.1"
PORT = 8000
WORKERS = 1
HOST_ENV = "SMART_DISPATCH_HOST"
PORT_ENV = "SMART_DISPATCH_PORT"


def _resolve_host() -> str:
    return os.environ.get(HOST_ENV, HOST)


def _resolve_port() -> int:
    selected = os.environ.get(PORT_ENV)
    if selected is None:
        return PORT
    try:
        port = int(selected)
    except ValueError as error:
        raise StartupError("SMART_DISPATCH_PORT must be an integer") from error
    if not 1 <= port <= 65535:
        raise StartupError("SMART_DISPATCH_PORT must be between 1 and 65535")
    return port


def run(
    *,
    prepare: Callable[[], None] | None = None,
    serve: Callable[..., None] | None = None,
) -> None:
    preparation = prepare or prepare_runtime
    server = serve or uvicorn.run
    preparation()
    server("app.main:app", host=_resolve_host(), port=_resolve_port(), workers=WORKERS)


def main() -> None:
    try:
        run()
    except StartupError as error:
        print(f"Smart Dispatch startup failed: {error}", file=sys.stderr)
        raise SystemExit(1) from None
