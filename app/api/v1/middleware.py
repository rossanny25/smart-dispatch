import json
from json import JSONDecodeError
import math
from uuid import uuid4

from app.api.v1.errors import error_response, is_canonical_v1_path


MAX_BODY_BYTES = 1_048_576


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"Unsupported JSON constant: {value}")


def _require_finite_json_numbers(value: object) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("JSON number exceeds the supported finite range.")
    if isinstance(value, list):
        for item in value:
            _require_finite_json_numbers(item)
    elif isinstance(value, dict):
        for item in value.values():
            _require_finite_json_numbers(item)


def _header(scope: dict, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return value.decode("latin-1")
    return None


def _is_json_media_type(value: str | None) -> bool:
    if value is None:
        return False
    parts = [part.strip() for part in value.lower().split(";")]
    if parts[0] != "application/json":
        return False
    parameters = parts[1:]
    return len(parameters) <= 1 and all(
        parameter.startswith("charset=") and len(parameter) > len("charset=")
        for parameter in parameters
    )


class CanonicalCommandMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if (
            scope["type"] != "http"
            or not is_canonical_v1_path(scope.get("path", ""))
        ):
            await self.app(scope, receive, send)
            return

        request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        if scope.get("method") not in {"POST", "PUT", "PATCH", "DELETE"}:
            await self.app(scope, receive, send)
            return
        media_type = _header(scope, b"content-type")
        if not _is_json_media_type(media_type):
            await error_response(
                request_id=request_id,
                status_code=415,
                code="UNSUPPORTED_MEDIA_TYPE",
            )(scope, receive, send)
            return

        idempotency_key = _header(scope, b"idempotency-key")
        if idempotency_key is None:
            await self._idempotency_error(
                scope,
                receive,
                send,
                request_id,
                "missing",
                "Header is required.",
            )
            return
        if not idempotency_key.strip():
            await self._idempotency_error(
                scope,
                receive,
                send,
                request_id,
                "blank",
                "Header must not be blank.",
            )
            return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            chunk = message.get("body", b"")
            if len(chunk) > MAX_BODY_BYTES - len(body):
                await error_response(
                    request_id=request_id,
                    status_code=413,
                    code="PAYLOAD_TOO_LARGE",
                )(scope, receive, send)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        try:
            decoded = json.loads(bytes(body), parse_constant=_reject_json_constant)
            _require_finite_json_numbers(decoded)
        except (JSONDecodeError, UnicodeDecodeError, ValueError, RecursionError):
            await error_response(
                request_id=request_id,
                status_code=422,
                code="VALIDATION_FAILED",
                details=[
                    {
                        "field": "body",
                        "code": "invalid_json",
                        "message": "Request body must be valid UTF-8 JSON.",
                    }
                ],
            )(scope, receive, send)
            return

        delivered = False

        async def replay_receive():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {
                    "type": "http.request",
                    "body": bytes(body),
                    "more_body": False,
                }
            return {"type": "http.disconnect"}

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def _idempotency_error(
        scope,
        receive,
        send,
        request_id: str,
        detail_code: str,
        detail_message: str,
    ) -> None:
        await error_response(
            request_id=request_id,
            status_code=422,
            code="VALIDATION_FAILED",
            details=[
                {
                    "field": "idempotency_key",
                    "code": detail_code,
                    "message": detail_message,
                }
            ],
        )(scope, receive, send)
