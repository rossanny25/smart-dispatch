from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from json import JSONDecodeError
from typing import Any
from uuid import UUID

from app.application.ports.persistence import (
    ConcurrentIdempotencyWrite,
    PersistenceAdapterError,
    UnitOfWorkFactory,
)
from app.domain.work_orders.models import IdempotencyRecord, WorkOrder


class IdempotencyConflict(RuntimeError):
    """The same idempotency scope/key was used for a different request."""


class CreateWorkOrderPersistenceError(RuntimeError):
    """The command could not commit safely."""


@dataclass(frozen=True)
class CreateWorkOrderRequest:
    raw_input: dict[str, Any]
    route: str
    idempotency_key: str
    request_id: str


@dataclass(frozen=True)
class CreateWorkOrderResult:
    status_code: int
    body: dict[str, Any]
    replayed: bool


def canonical_json(value: Mapping[str, Any] | dict[str, Any]) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_request_hash(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(dict(value)).encode("utf-8")).hexdigest()


def format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("UTC clock must return a timezone-aware datetime.")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class CreateWorkOrder:
    def __init__(
        self,
        *,
        unit_of_work_factory: UnitOfWorkFactory,
        uuid_factory: Callable[[], UUID],
        clock: Callable[[], datetime],
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._uuid_factory = uuid_factory
        self._clock = clock

    def execute(self, request: CreateWorkOrderRequest) -> CreateWorkOrderResult:
        request_hash = canonical_request_hash(request.raw_input)
        try:
            return self._execute_transaction(request, request_hash)
        except ConcurrentIdempotencyWrite:
            try:
                return self._resolve_race(request, request_hash)
            except PersistenceAdapterError as error:
                raise CreateWorkOrderPersistenceError from error
        except PersistenceAdapterError as error:
            raise CreateWorkOrderPersistenceError from error

    def _execute_transaction(
        self,
        request: CreateWorkOrderRequest,
        request_hash: str,
    ) -> CreateWorkOrderResult:
        with self._unit_of_work_factory() as unit_of_work:
            existing = unit_of_work.idempotency.get(
                request.route,
                request.idempotency_key,
            )
            if existing is not None:
                return self._existing_result(existing, request_hash)

            created_at = self._clock()
            work_order = WorkOrder(
                id=self._uuid_factory(),
                schema_version="v1",
                raw_input=request.raw_input,
                incident_text=request.raw_input["incident_text"],
                address=request.raw_input["address"],
                zone=request.raw_input["zone"],
                context=request.raw_input.get("context"),
                created_at=created_at,
            )
            body = {
                "data": {
                    "id": str(work_order.id),
                    "schema_version": "v1",
                    "raw_input": work_order.raw_input,
                    "created_at": format_utc(created_at),
                },
                "meta": {
                    "schema_version": "v1",
                    "request_id": request.request_id,
                },
            }
            unit_of_work.work_orders.add(work_order)
            unit_of_work.idempotency.add(
                IdempotencyRecord(
                    route=request.route,
                    idempotency_key=request.idempotency_key,
                    request_hash=request_hash,
                    response_status=201,
                    response_body_json=canonical_json(body),
                    created_at=created_at,
                )
            )
            return CreateWorkOrderResult(
                status_code=201,
                body=body,
                replayed=False,
            )

    def _resolve_race(
        self,
        request: CreateWorkOrderRequest,
        request_hash: str,
    ) -> CreateWorkOrderResult:
        with self._unit_of_work_factory() as unit_of_work:
            existing = unit_of_work.idempotency.get(
                request.route,
                request.idempotency_key,
            )
            if existing is None:
                raise CreateWorkOrderPersistenceError
            return self._existing_result(existing, request_hash)

    @staticmethod
    def _existing_result(
        existing: IdempotencyRecord,
        request_hash: str,
    ) -> CreateWorkOrderResult:
        if existing.request_hash != request_hash:
            raise IdempotencyConflict
        try:
            body = json.loads(existing.response_body_json)
        except (JSONDecodeError, TypeError) as error:
            raise CreateWorkOrderPersistenceError from error
        return CreateWorkOrderResult(
            status_code=existing.response_status,
            body=body,
            replayed=True,
        )
