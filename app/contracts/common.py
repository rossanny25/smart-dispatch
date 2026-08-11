from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ResponseMetaV1(StrictContract):
    schema_version: Literal["v1"] = "v1"
    request_id: UUID


class ErrorDetailV1(StrictContract):
    field: str
    code: str
    message: str


class ErrorV1(StrictContract):
    code: str
    message: str
    details: list[ErrorDetailV1]


class ErrorEnvelopeV1(StrictContract):
    schema_version: Literal["v1"] = "v1"
    error: ErrorV1
    meta: ResponseMetaV1

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        json_schema_extra={
            "examples": [
                {
                    "schema_version": "v1",
                    "error": {
                        "code": "VALIDATION_FAILED",
                        "message": "Request validation failed.",
                        "details": [
                            {
                                "field": "incident_text",
                                "code": "missing",
                                "message": "Field is required.",
                            }
                        ],
                    },
                    "meta": {
                        "schema_version": "v1",
                        "request_id": "22222222-2222-4222-8222-222222222222",
                    },
                }
            ]
        },
    )
