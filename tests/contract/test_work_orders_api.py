import json
import logging
from pathlib import Path
import re
import threading
import uuid

from fastapi import FastAPI
import pytest
from sqlalchemy import text

from app.adapters.persistence.database import create_sqlite_engine
from app.api.v1.middleware import CanonicalCommandMiddleware, MAX_BODY_BYTES
from app.api.v1.router import create_v1_router
from app.application.commands.create_work_order import CreateWorkOrderResult
from app.application.ports.persistence import PersistenceAdapterError
from app.contracts.common import ErrorEnvelopeV1
from app.contracts.work_orders import WorkOrderSuccessEnvelopeV1
from app.main import create_app
from app.startup import prepare_runtime
from tests.asgi_client import request_asgi


VALID_BODY = {
    "incident_text": "  Corte de energía en tablero principal  ",
    "address": "  Av. Siempre Viva 123  ",
    "zone": "  Belgrano  ",
    "context": {"source": "phone", "floors": [2, 3]},
}
HEADERS = {
    "content-type": "application/json; charset=utf-8",
    "idempotency-key": "dispatch-demo-1",
}


@pytest.fixture
def canonical_app(tmp_path: Path):
    database_path = tmp_path / "canonical.db"
    prepare_runtime(database_path)
    return create_app(database_path=database_path), database_path


def post(app, body: dict, *, headers: dict[str, str] | None = None):
    return request_asgi(
        app,
        "/api/v1/work-orders",
        method="POST",
        json_body=body,
        headers=headers or HEADERS,
    )


def table_counts(database_path: Path) -> tuple[int, int]:
    engine = create_sqlite_engine(database_path)
    try:
        with engine.connect() as connection:
            return (
                connection.execute(text("SELECT count(*) FROM work_orders")).scalar_one(),
                connection.execute(
                    text("SELECT count(*) FROM idempotency_records")
                ).scalar_one(),
            )
    finally:
        engine.dispose()


def assert_error(
    body: bytes,
    *,
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
) -> dict:
    payload = json.loads(body)
    assert payload["schema_version"] == "v1"
    assert payload["error"] == {
        "code": code,
        "message": message,
        "details": details or [],
    }
    assert payload["meta"]["schema_version"] == "v1"
    uuid.UUID(payload["meta"]["request_id"])
    return payload


def assert_generated_openapi_contract(
    app,
    *,
    status_code: int,
    body: bytes,
    model,
) -> None:
    document = app.openapi()
    response_schema = document["paths"]["/api/v1/work-orders"]["post"][
        "responses"
    ][str(status_code)]["content"]["application/json"]["schema"]
    assert response_schema == {
        "$ref": f"#/components/schemas/{model.__name__}"
    }

    standalone = model.model_json_schema(
        ref_template="#/components/schemas/{model}"
    )
    standalone.pop("$defs", {})
    components = document["components"]["schemas"]
    assert components[model.__name__] == standalone
    model.model_validate_json(body)


def test_valid_creation_preserves_semantic_input_and_persists_atomically(
    canonical_app,
) -> None:
    app, database_path = canonical_app

    status, _, body = post(app, VALID_BODY)

    assert status == 201
    payload = json.loads(body)
    assert set(payload) == {"data", "meta"}
    assert payload["meta"]["schema_version"] == "v1"
    uuid.UUID(payload["meta"]["request_id"])
    uuid.UUID(payload["data"]["id"])
    assert payload["data"]["schema_version"] == "v1"
    assert set(payload["data"]) == {
        "id",
        "schema_version",
        "raw_input",
        "created_at",
    }
    assert payload["data"]["raw_input"] == VALID_BODY
    assert re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z",
        payload["data"]["created_at"],
    )
    assert table_counts(database_path) == (1, 1)


@pytest.mark.parametrize(
    ("request_body", "field", "detail_code", "detail_message"),
    [
        (
            {"address": "A", "zone": "Z"},
            "incident_text",
            "missing",
            "Field is required.",
        ),
        (
            {"incident_text": 4, "address": "A", "zone": "Z"},
            "incident_text",
            "invalid_type",
            "Field has an invalid type.",
        ),
        (
            {"incident_text": " \t", "address": "A", "zone": "Z"},
            "incident_text",
            "blank",
            "Field must not be blank.",
        ),
        (
            {"incident_text": "I", "address": "A", "zone": "Z", "surprise": True},
            "surprise",
            "extra_forbidden",
            "Field is not supported.",
        ),
    ],
)
def test_contract_failures_have_stable_details_and_do_not_mutate(
    canonical_app,
    request_body,
    field,
    detail_code,
    detail_message,
) -> None:
    app, database_path = canonical_app

    status, _, body = post(app, request_body)

    assert status == 422
    assert_error(
        body,
        code="VALIDATION_FAILED",
        message="Request validation failed.",
        details=[
            {"field": field, "code": detail_code, "message": detail_message}
        ],
    )
    assert table_counts(database_path) == (0, 0)


@pytest.mark.parametrize(
    ("headers", "detail_code", "detail_message"),
    [
        ({"content-type": "application/json"}, "missing", "Header is required."),
        (
            {"content-type": "application/json", "idempotency-key": "  "},
            "blank",
            "Header must not be blank.",
        ),
    ],
)
def test_idempotency_header_is_required_before_command_execution(
    canonical_app,
    headers,
    detail_code,
    detail_message,
) -> None:
    app, database_path = canonical_app

    status, _, body = post(app, VALID_BODY, headers=headers)

    assert status == 422
    assert_error(
        body,
        code="VALIDATION_FAILED",
        message="Request validation failed.",
        details=[
            {
                "field": "idempotency_key",
                "code": detail_code,
                "message": detail_message,
            }
        ],
    )
    assert table_counts(database_path) == (0, 0)


def test_identical_retry_replays_original_response_and_changed_body_conflicts(
    canonical_app,
) -> None:
    app, database_path = canonical_app

    first = post(app, VALID_BODY)
    replay = post(
        app,
        {
            "zone": VALID_BODY["zone"],
            "context": {"floors": [2, 3], "source": "phone"},
            "address": VALID_BODY["address"],
            "incident_text": VALID_BODY["incident_text"],
        },
    )
    conflict = post(app, {**VALID_BODY, "zone": "Palermo"})

    assert first == replay
    assert conflict[0] == 409
    assert_error(
        conflict[2],
        code="CONFLICT",
        message="Idempotency key was already used with a different request.",
    )
    assert table_counts(database_path) == (1, 1)


def test_transport_rejections_are_stream_safe_and_do_not_mutate(canonical_app) -> None:
    app, database_path = canonical_app

    unsupported = request_asgi(
        app,
        "/api/v1/work-orders",
        method="POST",
        body=b"incident",
        headers={"content-type": "text/plain", "idempotency-key": "media"},
    )
    oversized = request_asgi(
        app,
        "/api/v1/work-orders",
        method="POST",
        body_chunks=[b"{" + b"x" * 700_000, b"x" * 400_000 + b"}"],
        headers={
            "content-type": "application/json",
            "content-length": "2",
            "idempotency-key": "large",
        },
    )

    assert unsupported[0] == 415
    assert_error(
        unsupported[2],
        code="UNSUPPORTED_MEDIA_TYPE",
        message="Content-Type must be application/json.",
    )
    assert oversized[0] == 413
    assert_error(
        oversized[2],
        code="PAYLOAD_TOO_LARGE",
        message="Request body exceeds 1 MiB.",
    )
    assert table_counts(database_path) == (0, 0)


def test_malformed_json_is_sanitized_and_does_not_mutate(canonical_app) -> None:
    app, database_path = canonical_app

    status, _, body = request_asgi(
        app,
        "/api/v1/work-orders",
        method="POST",
        body=b"\xff{",
        headers=HEADERS,
    )

    assert status == 422
    assert_error(
        body,
        code="VALIDATION_FAILED",
        message="Request validation failed.",
        details=[
            {
                "field": "body",
                "code": "invalid_json",
                "message": "Request body must be valid UTF-8 JSON.",
            }
        ],
    )
    assert table_counts(database_path) == (0, 0)


def test_nonstandard_json_constant_is_rejected(canonical_app) -> None:
    app, database_path = canonical_app

    status, _, body = request_asgi(
        app,
        "/api/v1/work-orders",
        method="POST",
        body=(
            b'{"incident_text":"I","address":"A","zone":"Z",'
            b'"context":{"value":NaN}}'
        ),
        headers=HEADERS,
    )

    assert status == 422
    assert_error(
        body,
        code="VALIDATION_FAILED",
        message="Request validation failed.",
        details=[
            {
                "field": "body",
                "code": "invalid_json",
                "message": "Request body must be valid UTF-8 JSON.",
            }
        ],
    )
    assert table_counts(database_path) == (0, 0)


def test_json_number_overflow_is_rejected_before_idempotency_hashing(
    canonical_app,
) -> None:
    app, database_path = canonical_app

    overflow = request_asgi(
        app,
        "/api/v1/work-orders",
        method="POST",
        body=(
            b'{"incident_text":"I","address":"A","zone":"Z",'
            b'"context":{"value":1e400}}'
        ),
        headers=HEADERS,
    )
    explicit_null = post(
        app,
        {
            "incident_text": "I",
            "address": "A",
            "zone": "Z",
            "context": {"value": None},
        },
    )

    assert overflow[0] == 422
    assert_error(
        overflow[2],
        code="VALIDATION_FAILED",
        message="Request validation failed.",
        details=[
            {
                "field": "body",
                "code": "invalid_json",
                "message": "Request body must be valid UTF-8 JSON.",
            }
        ],
    )
    assert explicit_null[0] == 201
    assert table_counts(database_path) == (1, 1)


def test_excessive_json_nesting_returns_stable_validation_error(
    canonical_app,
) -> None:
    app, database_path = canonical_app
    nested = b"[" * 10_000 + b"]" * 10_000

    status, _, body = request_asgi(
        app,
        "/api/v1/work-orders",
        method="POST",
        body=nested,
        headers=HEADERS,
    )

    assert status == 422
    assert_error(
        body,
        code="VALIDATION_FAILED",
        message="Request validation failed.",
        details=[
            {
                "field": "body",
                "code": "invalid_json",
                "message": "Request body must be valid UTF-8 JSON.",
            }
        ],
    )
    assert table_counts(database_path) == (0, 0)


def test_v1_path_boundary_does_not_capture_v10() -> None:
    status, _, _ = request_asgi(
        create_app(),
        "/api/v10/nope",
        method="POST",
        body=b"",
    )

    assert status == 404


def test_oversized_single_chunk_is_rejected_before_buffer_copy(
    canonical_app,
    monkeypatch,
) -> None:
    from app.api.v1 import middleware

    class GuardedBuffer(bytearray):
        def extend(self, value) -> None:
            if len(self) + len(value) > MAX_BODY_BYTES:
                raise AssertionError("oversized chunk copied before rejection")
            super().extend(value)

    monkeypatch.setattr(middleware, "bytearray", GuardedBuffer, raising=False)
    app, database_path = canonical_app

    status, _, _ = request_asgi(
        app,
        "/api/v1/work-orders",
        method="POST",
        body=b"x" * (MAX_BODY_BYTES + 1),
        headers=HEADERS,
    )

    assert status == 413
    assert table_counts(database_path) == (0, 0)


def test_valid_json_body_at_exact_size_limit_is_accepted(canonical_app) -> None:
    app, database_path = canonical_app
    prefix = b'{"incident_text":"'
    suffix = b'","address":"A","zone":"Z"}'
    payload = prefix + b"x" * (MAX_BODY_BYTES - len(prefix) - len(suffix)) + suffix
    assert len(payload) == MAX_BODY_BYTES

    status, _, _ = request_asgi(
        app,
        "/api/v1/work-orders",
        method="POST",
        body=payload,
        headers=HEADERS,
    )

    assert status == 201
    assert table_counts(database_path) == (1, 1)


def test_openapi_declares_canonical_operation_and_all_responses(canonical_app) -> None:
    app, _ = canonical_app

    status, _, body = request_asgi(app, "/openapi.json")

    assert status == 200
    operation = json.loads(body)["paths"]["/api/v1/work-orders"]["post"]
    assert operation["requestBody"]["required"] is True
    header = next(
        parameter
        for parameter in operation["parameters"]
        if parameter["name"] == "Idempotency-Key"
    )
    assert header["required"] is True
    assert set(operation["responses"]) >= {
        "201",
        "409",
        "413",
        "415",
        "422",
        "500",
    }
    components = json.loads(body)["components"]["schemas"]
    WorkOrderSuccessEnvelopeV1.model_validate_json(
        json.dumps(components["WorkOrderSuccessEnvelopeV1"]["examples"][0])
    )
    ErrorEnvelopeV1.model_validate_json(
        json.dumps(components["ErrorEnvelopeV1"]["examples"][0])
    )


def test_persistence_failure_is_sanitized() -> None:
    class FailingFactory:
        def __call__(self):
            raise PersistenceAdapterError(
                "sqlite /Users/private/dispatch.db incident at Avenida 123"
            )

    app = create_app(unit_of_work_factory=FailingFactory())

    status, _, body = post(app, VALID_BODY)

    assert status == 500
    payload = assert_error(
        body,
        code="PERSISTENCE_ERROR",
        message="Work Order could not be created.",
    )
    rendered = json.dumps(payload)
    assert "sqlite" not in rendered
    assert "/Users/" not in rendered
    assert VALID_BODY["address"] not in rendered


def test_corrupted_retained_response_maps_to_safe_persistence_error(
    canonical_app,
) -> None:
    app, database_path = canonical_app
    assert post(app, VALID_BODY)[0] == 201
    engine = create_sqlite_engine(database_path)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE idempotency_records "
                    "SET response_status = 299, response_body_json = '[]'"
                )
            )
    finally:
        engine.dispose()

    status, _, body = post(app, VALID_BODY)

    assert status == 500
    assert_error(
        body,
        code="PERSISTENCE_ERROR",
        message="Work Order could not be created.",
    )


def test_canonical_middleware_does_not_change_legacy_media_handling() -> None:
    app = create_app()

    status, _, _ = request_asgi(
        app,
        "/api/orders",
        method="POST",
        body=b"not-json",
        headers={"content-type": "text/plain"},
    )

    assert status != 415


def test_actual_success_and_every_error_validate_against_generated_openapi(
    canonical_app,
) -> None:
    app, _ = canonical_app
    success = post(app, VALID_BODY)
    conflict = post(app, {**VALID_BODY, "zone": "Sur"})
    validation = post(app, {"address": "A", "zone": "Z"})
    unsupported = request_asgi(
        app,
        "/api/v1/work-orders",
        method="POST",
        body=b"plain",
        headers={"content-type": "text/plain", "idempotency-key": "media"},
    )
    oversized = request_asgi(
        app,
        "/api/v1/work-orders",
        method="POST",
        body=b"x" * (1_048_576 + 1),
        headers={"content-type": "application/json", "idempotency-key": "large"},
    )

    class FailingFactory:
        def __call__(self):
            raise PersistenceAdapterError("private database failure")

    persistence = post(
        create_app(unit_of_work_factory=FailingFactory()),
        VALID_BODY,
    )

    assert_generated_openapi_contract(
        app,
        status_code=success[0],
        body=success[2],
        model=WorkOrderSuccessEnvelopeV1,
    )
    for response in (conflict, validation, unsupported, oversized):
        assert_generated_openapi_contract(
            app,
            status_code=response[0],
            body=response[2],
            model=ErrorEnvelopeV1,
        )
    assert_generated_openapi_contract(
        create_app(unit_of_work_factory=FailingFactory()),
        status_code=persistence[0],
        body=persistence[2],
        model=ErrorEnvelopeV1,
    )


def test_validation_details_have_deterministic_field_then_code_order(
    canonical_app,
) -> None:
    app, _ = canonical_app

    status, _, body = post(app, {"surprise": True})

    assert status == 422
    assert [
        item["field"] for item in json.loads(body)["error"]["details"]
    ] == ["address", "incident_text", "surprise", "zone"]


def test_emitted_operation_logs_are_json_and_omit_request_content(
    canonical_app,
    caplog,
) -> None:
    app, _ = canonical_app
    caplog.set_level(logging.INFO, logger="smart_dispatch.operations")

    post(app, VALID_BODY)
    post(app, {"incident_text": " ", "address": "PRIVATE", "zone": "SECRET"})

    events = [json.loads(record.message) for record in caplog.records]
    assert {event["status"] for event in events} >= {"created", "rejected"}
    assert all(
        {"request_id", "operation", "status"} <= set(event)
        for event in events
    )
    rendered = "\n".join(record.message for record in caplog.records)
    assert VALID_BODY["address"] not in rendered
    assert VALID_BODY["incident_text"] not in rendered
    assert "PRIVATE" not in rendered
    assert "SECRET" not in rendered


def test_synchronous_command_runs_off_the_event_loop_thread() -> None:
    caller_thread = threading.get_ident()

    class ThreadRecordingCommand:
        execution_thread: int | None = None

        def execute(self, request):
            self.execution_thread = threading.get_ident()
            return CreateWorkOrderResult(
                status_code=201,
                body={
                    "data": {
                        "id": "11111111-1111-4111-8111-111111111111",
                        "schema_version": "v1",
                        "raw_input": request.raw_input,
                        "created_at": "2026-07-28T12:30:00Z",
                    },
                    "meta": {
                        "schema_version": "v1",
                        "request_id": request.request_id,
                    },
                },
                replayed=False,
            )

    command = ThreadRecordingCommand()
    app = FastAPI()
    app.add_middleware(CanonicalCommandMiddleware)
    app.include_router(create_v1_router(command))

    status, _, _ = post(app, VALID_BODY)

    assert status == 201
    assert command.execution_thread is not None
    assert command.execution_thread != caller_thread
