from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Request
from fastapi.responses import Response
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from app.api.v1.errors import emit_operation_log, error_response
from app.application.commands.analyze_work_order import WorkOrderNotFound
from app.application.commands.execute_dispatch_run import (
    DispatchIdempotencyConflict,
    DispatchOrchestrator,
    DispatchRunNotFound,
    DispatchRunExecutionFailed,
    DispatchRunPersistenceError,
    ExecuteDispatchRunRequest,
)
from app.contracts.common import ErrorEnvelopeV1
from app.contracts.dispatch_runs import (
    DispatchRunStartV1,
    DispatchRunSuccessEnvelopeV1,
)
from app.domain.scoring.rules import canonical_json


ROUTE_SCOPE = "/api/v1/dispatch-runs"


def create_dispatch_runs_router(orchestrator: DispatchOrchestrator) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/dispatch-runs",
        status_code=201,
        response_model=DispatchRunSuccessEnvelopeV1,
        responses={
            404: {"model": ErrorEnvelopeV1},
            409: {"model": ErrorEnvelopeV1},
            413: {"model": ErrorEnvelopeV1},
            415: {"model": ErrorEnvelopeV1},
            422: {"model": ErrorEnvelopeV1},
            500: {"model": ErrorEnvelopeV1},
        },
    )
    async def execute_dispatch_run(
        request: Request,
        dispatch_input: DispatchRunStartV1,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    ) -> Response:
        try:
            result = await run_in_threadpool(
                orchestrator.execute,
                ExecuteDispatchRunRequest(
                    input=dispatch_input,
                    route=ROUTE_SCOPE,
                    idempotency_key=idempotency_key,
                    request_id=request.state.request_id,
                ),
            )
            body_json = canonical_json(result.body)
            DispatchRunSuccessEnvelopeV1.model_validate_json(body_json)
            emit_operation_log(
                request_id=request.state.request_id,
                status="replayed" if result.replayed else "completed",
                operation="execute_dispatch_run",
            )
            return Response(
                status_code=201,
                content=body_json,
                media_type="application/json",
                headers={"Idempotent-Replay": "true" if result.replayed else "false"},
            )
        except DispatchIdempotencyConflict:
            return error_response(
                request_id=request.state.request_id,
                status_code=409,
                code="CONFLICT",
                operation="execute_dispatch_run",
            )
        except WorkOrderNotFound:
            return error_response(
                request_id=request.state.request_id,
                status_code=404,
                code="WORK_ORDER_NOT_FOUND",
                operation="execute_dispatch_run",
            )
        except DispatchRunExecutionFailed as error:
            return error_response(
                request_id=request.state.request_id,
                status_code=500,
                code="DISPATCH_RUN_FAILED",
                details=[
                    {
                        "field": "run_id",
                        "code": "retained_failed_run",
                        "message": str(error.run_id),
                    }
                ],
                operation="execute_dispatch_run",
            )
        except (DispatchRunPersistenceError, ValidationError, ValueError):
            return error_response(
                request_id=request.state.request_id,
                status_code=500,
                code="DISPATCH_RUN_FAILED",
                operation="execute_dispatch_run",
            )

    @router.get(
        "/dispatch-runs/{run_id}",
        response_model=DispatchRunSuccessEnvelopeV1,
        responses={
            404: {"model": ErrorEnvelopeV1},
            500: {"model": ErrorEnvelopeV1},
        },
    )
    async def get_dispatch_run(request: Request, run_id: str) -> Response:
        request_id = request.state.request_id
        try:
            resource = await run_in_threadpool(orchestrator.get, run_id)
            body = DispatchRunSuccessEnvelopeV1.model_validate(
                {
                    "data": resource,
                    "meta": {"request_id": UUID(request_id)},
                }
            )
            return Response(
                status_code=200,
                content=canonical_json(body.model_dump(mode="json")),
                media_type="application/json",
            )
        except DispatchRunNotFound:
            return error_response(
                request_id=request_id,
                status_code=404,
                code="RUN_NOT_FOUND",
                operation="get_dispatch_run",
            )
        except (DispatchRunPersistenceError, ValidationError, ValueError):
            return error_response(
                request_id=request_id,
                status_code=500,
                code="PERSISTENCE_ERROR",
                operation="get_dispatch_run",
            )

    return router
