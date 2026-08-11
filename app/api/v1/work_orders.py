from typing import Annotated

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.api.v1.errors import emit_operation_log, error_response
from app.application.commands.create_work_order import (
    CreateWorkOrder,
    CreateWorkOrderPersistenceError,
    CreateWorkOrderRequest,
    IdempotencyConflict,
    canonical_json,
)
from app.contracts.common import ErrorEnvelopeV1
from app.contracts.work_orders import WorkOrderCreateV1, WorkOrderSuccessEnvelopeV1


ROUTE_SCOPE = "/api/v1/work-orders"


def create_work_orders_router(command: CreateWorkOrder) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/work-orders",
        status_code=201,
        response_model=WorkOrderSuccessEnvelopeV1,
        responses={
            409: {"model": ErrorEnvelopeV1},
            413: {"model": ErrorEnvelopeV1},
            415: {"model": ErrorEnvelopeV1},
            422: {"model": ErrorEnvelopeV1},
            500: {"model": ErrorEnvelopeV1},
        },
    )
    async def create_work_order(
        request: Request,
        work_order: WorkOrderCreateV1,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    ) -> Response:
        try:
            command_request = CreateWorkOrderRequest(
                raw_input=work_order.model_dump(mode="json", exclude_none=False),
                route=ROUTE_SCOPE,
                idempotency_key=idempotency_key,
                request_id=request.state.request_id,
            )
            result = await run_in_threadpool(command.execute, command_request)
        except IdempotencyConflict:
            return error_response(
                request_id=request.state.request_id,
                status_code=409,
                code="CONFLICT",
            )
        except CreateWorkOrderPersistenceError:
            return error_response(
                request_id=request.state.request_id,
                status_code=500,
                code="PERSISTENCE_ERROR",
            )

        try:
            if result.status_code != 201:
                raise ValueError("Retained success status is invalid.")
            rendered_body = canonical_json(result.body)
            WorkOrderSuccessEnvelopeV1.model_validate_json(rendered_body)
        except (TypeError, ValueError, ValidationError):
            return error_response(
                request_id=request.state.request_id,
                status_code=500,
                code="PERSISTENCE_ERROR",
            )

        emit_operation_log(
            request_id=request.state.request_id,
            status="replayed" if result.replayed else "created",
        )
        return Response(
            status_code=result.status_code,
            content=rendered_body,
            media_type="application/json",
        )

    return router
