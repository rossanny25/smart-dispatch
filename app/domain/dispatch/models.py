from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class DispatchRun:
    id: UUID
    work_order_id: UUID
    state: str
    revision: int
    snapshot_json: str
    snapshot_sha256: str
    resource_json: str
    created_at: datetime
    updated_at: datetime
