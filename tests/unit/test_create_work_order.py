from datetime import UTC, datetime
import json
from uuid import UUID

import pytest

from app.api.v1.errors import operation_log
from app.application.commands.create_work_order import (
    CreateWorkOrder,
    CreateWorkOrderRequest,
    IdempotencyConflict,
    canonical_request_hash,
)
from app.application.ports.persistence import ConcurrentIdempotencyWrite
from app.domain.work_orders.models import IdempotencyRecord, WorkOrder


NOW = datetime(2026, 7, 28, 12, 30, tzinfo=UTC)
WORK_ORDER_ID = UUID("11111111-1111-4111-8111-111111111111")
RAW_INPUT = {
    "incident_text": "Corte de energía",
    "address": "Av. Siempre Viva 123",
    "zone": "Belgrano",
    "context": None,
}


class FakeWorkOrders:
    def __init__(self, rows: list[WorkOrder]):
        self.rows = rows

    def add(self, work_order: WorkOrder) -> None:
        self.rows.append(work_order)

    def get(self, work_order_id: str) -> WorkOrder | None:
        return next(
            (row for row in self.rows if str(row.id) == work_order_id),
            None,
        )


class FakeIdempotency:
    def __init__(self, rows: dict[tuple[str, str], IdempotencyRecord]):
        self.rows = rows

    def get(self, route: str, key: str) -> IdempotencyRecord | None:
        return self.rows.get((route, key))

    def add(self, record: IdempotencyRecord) -> None:
        self.rows[(record.route, record.idempotency_key)] = record


class FakeUnitOfWork:
    def __init__(self, work_orders, idempotency):
        self.work_orders = work_orders
        self.idempotency = idempotency

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class FakeUnitOfWorkFactory:
    def __init__(self):
        self.work_order_rows: list[WorkOrder] = []
        self.idempotency_rows: dict[tuple[str, str], IdempotencyRecord] = {}

    def __call__(self):
        return FakeUnitOfWork(
            FakeWorkOrders(self.work_order_rows),
            FakeIdempotency(self.idempotency_rows),
        )


def build_command(factory: FakeUnitOfWorkFactory) -> CreateWorkOrder:
    return CreateWorkOrder(
        unit_of_work_factory=factory,
        uuid_factory=lambda: WORK_ORDER_ID,
        clock=lambda: NOW,
    )


def command_request(
    *,
    raw_input: dict | None = None,
    request_id: str = "22222222-2222-4222-8222-222222222222",
) -> CreateWorkOrderRequest:
    return CreateWorkOrderRequest(
        raw_input=raw_input or RAW_INPUT,
        route="/api/v1/work-orders",
        idempotency_key="key-1",
        request_id=request_id,
    )


def test_canonical_request_hash_ignores_json_object_order_and_whitespace() -> None:
    first = {"zone": "Z", "context": {"b": 2, "a": 1}}
    second = json.loads(' { "context": { "a": 1, "b": 2 }, "zone": "Z" } ')

    assert canonical_request_hash(first) == canonical_request_hash(second)
    assert len(canonical_request_hash(first)) == 64


def test_command_creates_one_work_order_and_replays_complete_original_body() -> None:
    factory = FakeUnitOfWorkFactory()
    command = build_command(factory)

    first = command.execute(command_request())
    replay = command.execute(
        command_request(request_id="33333333-3333-4333-8333-333333333333")
    )

    assert first.status_code == replay.status_code
    assert first.body == replay.body
    assert first.status_code == 201
    assert first.replayed is False
    assert replay.replayed is True
    assert first.body["data"]["id"] == str(WORK_ORDER_ID)
    assert first.body["data"]["raw_input"] == RAW_INPUT
    assert first.body["data"]["created_at"] == "2026-07-28T12:30:00Z"
    assert first.body["meta"]["request_id"] == "22222222-2222-4222-8222-222222222222"
    assert len(factory.work_order_rows) == 1
    assert len(factory.idempotency_rows) == 1


def test_command_rejects_same_route_and_key_with_different_hash() -> None:
    factory = FakeUnitOfWorkFactory()
    command = build_command(factory)
    command.execute(command_request())

    with pytest.raises(IdempotencyConflict):
        command.execute(command_request(raw_input={**RAW_INPUT, "zone": "Palermo"}))

    assert len(factory.work_order_rows) == 1


class RacingIdempotency:
    def get(self, route: str, key: str) -> None:
        return None

    def add(self, record: IdempotencyRecord) -> None:
        raise ConcurrentIdempotencyWrite


class RaceRecoveryFactory:
    def __init__(self, winning_record: IdempotencyRecord):
        self.winning_record = winning_record
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.calls == 1:
            return FakeUnitOfWork(FakeWorkOrders([]), RacingIdempotency())
        return FakeUnitOfWork(
            FakeWorkOrders([]),
            FakeIdempotency(
                {
                    (
                        self.winning_record.route,
                        self.winning_record.idempotency_key,
                    ): self.winning_record
                }
            ),
        )


def winning_record(raw_input: dict) -> IdempotencyRecord:
    body = {
        "data": {
            "id": str(WORK_ORDER_ID),
            "schema_version": "v1",
            "raw_input": raw_input,
            "created_at": "2026-07-28T12:30:00Z",
        },
        "meta": {
            "schema_version": "v1",
            "request_id": "22222222-2222-4222-8222-222222222222",
        },
    }
    return IdempotencyRecord(
        route="/api/v1/work-orders",
        idempotency_key="key-1",
        request_hash=canonical_request_hash(raw_input),
        response_status=201,
        response_body_json=json.dumps(body),
        created_at=NOW,
    )


def test_uniqueness_race_replays_the_winning_identical_response() -> None:
    factory = RaceRecoveryFactory(winning_record(RAW_INPUT))
    result = build_command(factory).execute(command_request())

    assert result.replayed is True
    assert result.body["data"]["id"] == str(WORK_ORDER_ID)
    assert factory.calls == 2


def test_uniqueness_race_applies_normal_hash_conflict_rule() -> None:
    factory = RaceRecoveryFactory(winning_record({**RAW_INPUT, "zone": "Palermo"}))

    with pytest.raises(IdempotencyConflict):
        build_command(factory).execute(command_request())

    assert factory.calls == 2


def test_operation_log_is_structured_and_contains_no_private_input() -> None:
    rendered = operation_log(
        request_id="22222222-2222-4222-8222-222222222222",
        status="rejected",
        error_code="VALIDATION_FAILED",
    )

    assert json.loads(rendered) == {
        "error_code": "VALIDATION_FAILED",
        "operation": "create_work_order",
        "request_id": "22222222-2222-4222-8222-222222222222",
        "status": "rejected",
    }
    assert "Avenida" not in rendered
    assert "Corte de energía" not in rendered
