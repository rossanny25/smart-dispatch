from datetime import UTC, datetime
import json

from sqlalchemy import Connection, insert, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.adapters.persistence.schema import idempotency_records, work_orders
from app.application.ports.persistence import (
    ConcurrentIdempotencyWrite,
    PersistenceAdapterError,
)
from app.domain.work_orders.models import IdempotencyRecord, WorkOrder


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _format_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class SqlWorkOrderRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, work_order: WorkOrder) -> None:
        try:
            self._connection.execute(
                insert(work_orders),
                {
                    "id": str(work_order.id),
                    "schema_version": work_order.schema_version,
                    "raw_input_json": _canonical_json(work_order.raw_input),
                    "incident_text": work_order.incident_text,
                    "address": work_order.address,
                    "zone": work_order.zone,
                    "context_json": _canonical_json(work_order.context),
                    "created_at": _format_utc(work_order.created_at),
                },
            )
        except SQLAlchemyError as error:
            raise PersistenceAdapterError from error

    def get(self, work_order_id: str) -> WorkOrder | None:
        try:
            row = self._connection.execute(
                select(work_orders).where(work_orders.c.id == work_order_id)
            ).mappings().one_or_none()
            if row is None:
                return None
            from uuid import UUID

            return WorkOrder(
                id=UUID(row["id"]),
                schema_version=row["schema_version"],
                raw_input=json.loads(row["raw_input_json"]),
                incident_text=row["incident_text"],
                address=row["address"],
                zone=row["zone"],
                context=json.loads(row["context_json"]),
                created_at=_parse_datetime(row["created_at"]),
            )
        except (SQLAlchemyError, TypeError, ValueError, RecursionError) as error:
            raise PersistenceAdapterError from error


class SqlIdempotencyRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get(self, route: str, key: str) -> IdempotencyRecord | None:
        try:
            row = self._connection.execute(
                select(idempotency_records).where(
                    idempotency_records.c.route == route,
                    idempotency_records.c.idempotency_key == key,
                )
            ).mappings().one_or_none()
            if row is None:
                return None
            return IdempotencyRecord(
                route=row["route"],
                idempotency_key=row["idempotency_key"],
                request_hash=row["request_hash"],
                response_status=row["response_status"],
                response_body_json=row["response_body_json"],
                created_at=_parse_datetime(row["created_at"]),
            )
        except (SQLAlchemyError, TypeError, ValueError, RecursionError) as error:
            raise PersistenceAdapterError from error

    def add(self, record: IdempotencyRecord) -> None:
        try:
            self._connection.execute(
                insert(idempotency_records),
                {
                    "route": record.route,
                    "idempotency_key": record.idempotency_key,
                    "request_hash": record.request_hash,
                    "response_status": record.response_status,
                    "response_body_json": record.response_body_json,
                    "created_at": _format_utc(record.created_at),
                },
            )
        except IntegrityError as error:
            raise ConcurrentIdempotencyWrite from error
        except SQLAlchemyError as error:
            raise PersistenceAdapterError from error
