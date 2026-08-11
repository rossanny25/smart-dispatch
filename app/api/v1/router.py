from fastapi import APIRouter

from app.api.v1.work_orders import create_work_orders_router
from app.api.v1.dispatch_runs import create_dispatch_runs_router
from app.application.commands.create_work_order import CreateWorkOrder
from app.application.commands.execute_dispatch_run import DispatchOrchestrator


def create_v1_router(
    command: CreateWorkOrder,
    dispatch_orchestrator: DispatchOrchestrator | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    router.include_router(create_work_orders_router(command))
    if dispatch_orchestrator is not None:
        router.include_router(create_dispatch_runs_router(dispatch_orchestrator))
    return router
