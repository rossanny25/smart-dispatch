from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import AfterValidator, ConfigDict
from pydantic_core import PydanticCustomError

from app.contracts.common import ResponseMetaV1, StrictContract


def _reject_blank(value: str) -> str:
    if not value.strip():
        raise PydanticCustomError("string_blank", "Field must not be blank.")
    return value


NonBlankString = Annotated[str, AfterValidator(_reject_blank)]


class WorkOrderCreateV1(StrictContract):
    incident_text: NonBlankString
    address: NonBlankString
    zone: NonBlankString
    context: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid", strict=True)


class WorkOrderV1(StrictContract):
    id: UUID
    schema_version: Literal["v1"] = "v1"
    raw_input: WorkOrderCreateV1
    created_at: datetime


class WorkOrderSuccessEnvelopeV1(StrictContract):
    data: WorkOrderV1
    meta: ResponseMetaV1

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "data": {
                        "id": "11111111-1111-4111-8111-111111111111",
                        "schema_version": "v1",
                        "raw_input": {
                            "incident_text": "Corte de energía",
                            "address": "Av. Siempre Viva 123",
                            "zone": "Belgrano",
                            "context": {"source": "phone"},
                        },
                        "created_at": "2026-07-28T12:30:00Z",
                    },
                    "meta": {
                        "schema_version": "v1",
                        "request_id": "22222222-2222-4222-8222-222222222222",
                    },
                }
            ]
        },
    )
