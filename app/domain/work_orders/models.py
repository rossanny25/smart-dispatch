from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class WorkOrder:
    id: UUID
    schema_version: str
    raw_input: dict[str, Any]
    incident_text: str
    address: str
    zone: str
    context: dict[str, Any] | None
    created_at: datetime


@dataclass(frozen=True)
class IdempotencyRecord:
    route: str
    idempotency_key: str
    request_hash: str
    response_status: int
    response_body_json: str
    created_at: datetime

