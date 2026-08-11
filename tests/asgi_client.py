import asyncio
import json
from collections.abc import Mapping, Sequence
from typing import Any


def request_asgi(
    app: object,
    path: str,
    *,
    method: str = "GET",
    json_body: dict[str, Any] | None = None,
    body: bytes | None = None,
    body_chunks: Sequence[bytes] | None = None,
    headers: Mapping[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    if sum(value is not None for value in (json_body, body, body_chunks)) > 1:
        raise ValueError("Provide only one of json_body, body, or body_chunks.")

    messages: list[dict[str, object]] = []
    payload = json.dumps(json_body).encode() if json_body is not None else body or b""
    chunks = list(body_chunks) if body_chunks is not None else [payload]
    request_index = 0

    async def receive() -> dict[str, object]:
        nonlocal request_index
        if request_index < len(chunks):
            chunk = chunks[request_index]
            request_index += 1
            return {
                "type": "http.request",
                "body": chunk,
                "more_body": request_index < len(chunks),
            }
        return {"type": "http.disconnect"}

    async def send(message: dict[str, object]) -> None:
        messages.append(message)

    raw_headers = [
        (key.lower().encode(), value.encode())
        for key, value in (headers or {}).items()
    ]
    if json_body is not None:
        header_names = {key for key, _ in raw_headers}
        if b"content-type" not in header_names:
            raw_headers.append((b"content-type", b"application/json"))
        if b"content-length" not in header_names:
            raw_headers.append((b"content-length", str(len(payload)).encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": raw_headers,
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
    response_headers = {
        key.decode().lower(): value.decode()
        for key, value in start["headers"]  # type: ignore[index]
    }
    return int(start["status"]), response_headers, body  # type: ignore[arg-type]
