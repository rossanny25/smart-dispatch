import json
import logging
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import request_validation_exception_handler

from app.contracts.common import ErrorDetailV1


LOGGER = logging.getLogger("smart_dispatch.operations")

ERROR_MESSAGES = {
    "VALIDATION_FAILED": "Request validation failed.",
    "UNSUPPORTED_MEDIA_TYPE": "Content-Type must be application/json.",
    "PAYLOAD_TOO_LARGE": "Request body exceeds 1 MiB.",
    "CONFLICT": "Idempotency key was already used with a different request.",
    "PERSISTENCE_ERROR": "Work Order could not be created.",
    "WORK_ORDER_NOT_FOUND": "Work Order was not found.",
    "RUN_NOT_FOUND": "Dispatch run was not found.",
    "DISPATCH_RUN_FAILED": "Dispatch run could not be completed safely.",
}


def is_canonical_v1_path(path: str) -> bool:
    return path == "/api/v1" or path.startswith("/api/v1/")


def operation_log(
    *,
    request_id: str,
    status: str,
    error_code: str | None = None,
    operation: str = "create_work_order",
) -> str:
    event = {
        "request_id": request_id,
        "operation": operation,
        "status": status,
    }
    if error_code is not None:
        event["error_code"] = error_code
    return json.dumps(event, sort_keys=True, separators=(",", ":"))


def emit_operation_log(
    *,
    request_id: str,
    status: str,
    error_code: str | None = None,
    operation: str = "create_work_order",
) -> None:
    LOGGER.info(
        operation_log(
            request_id=request_id,
            status=status,
            error_code=error_code,
            operation=operation,
        )
    )


def error_payload(
    *,
    request_id: str,
    code: str,
    details: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "v1",
        "error": {
            "code": code,
            "message": ERROR_MESSAGES[code],
            "details": details or [],
        },
        "meta": {
            "schema_version": "v1",
            "request_id": request_id,
        },
    }


def error_response(
    *,
    request_id: str,
    status_code: int,
    code: str,
    details: list[dict[str, str]] | None = None,
    operation: str = "create_work_order",
) -> JSONResponse:
    emit_operation_log(
        request_id=request_id,
        status="rejected" if status_code < 500 else "failed",
        error_code=code,
        operation=operation,
    )
    return JSONResponse(
        status_code=status_code,
        content=error_payload(
            request_id=request_id,
            code=code,
            details=details,
        ),
    )


def _stable_detail(error: dict[str, Any]) -> ErrorDetailV1:
    error_type = str(error.get("type", ""))
    location = list(error.get("loc", ()))
    if location and location[0] == "body":
        location = location[1:]

    if error_type == "json_invalid":
        return ErrorDetailV1(
            field="body",
            code="invalid_json",
            message="Request body must be valid UTF-8 JSON.",
        )

    field = ".".join(str(part) for part in location) or "body"
    if error_type == "missing":
        code, message = "missing", "Field is required."
    elif error_type == "string_blank":
        code, message = "blank", "Field must not be blank."
    elif error_type == "extra_forbidden":
        code, message = "extra_forbidden", "Field is not supported."
    else:
        code, message = "invalid_type", "Field has an invalid type."
    return ErrorDetailV1(field=field, code=code, message=message)


async def canonical_validation_exception_handler(
    request: Request,
    exception: RequestValidationError,
):
    if not is_canonical_v1_path(request.url.path):
        return await request_validation_exception_handler(request, exception)

    details = sorted(
        (_stable_detail(error) for error in exception.errors()),
        key=lambda item: (item.field, item.code),
    )
    return error_response(
        request_id=request.state.request_id,
        status_code=422,
        code="VALIDATION_FAILED",
        details=[detail.model_dump() for detail in details],
    )
