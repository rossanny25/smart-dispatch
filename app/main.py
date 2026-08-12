"""FastAPI composition root.

Importing this module is intentionally side-effect free. Runtime preparation
(database validation, backup, and migrations) belongs to ``app.runtime``.
"""

from pathlib import Path
from datetime import UTC, datetime
from collections.abc import Callable
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from app.auth import (
    attach_session_cookie,
    clear_session_cookie,
    credentials_are_valid,
    read_login_credentials,
    request_is_authenticated,
    unauthenticated_response,
)
from app.adapters.persistence.unit_of_work import SqliteUnitOfWorkFactory
from app.adapters.legacy.compatibility import router as legacy_router
from app.api.v1.errors import canonical_validation_exception_handler
from app.api.v1.middleware import CanonicalCommandMiddleware
from app.api.v1.router import create_v1_router
from app.application.commands.create_work_order import CreateWorkOrder
from app.application.commands.execute_dispatch_run import DispatchOrchestrator
from app.adapters.stages.deterministic_analyze import DeterministicAnalyzeStage
from app.application.ports.persistence import UnitOfWorkFactory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
PUBLIC_PATHS = {
    "/healthz",
    "/login",
    "/auth/login",
    "/index.css",
}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def create_app(
    *,
    database_path: str | Path | None = None,
    unit_of_work_factory: UnitOfWorkFactory | None = None,
    uuid_factory: Callable[[], UUID] = uuid4,
    clock: Callable[[], datetime] = _utc_now,
) -> FastAPI:
    application = FastAPI(title="Smart Dispatch IA", version="2.1.0")
    concrete_factory = unit_of_work_factory or SqliteUnitOfWorkFactory(database_path)
    command = CreateWorkOrder(
        unit_of_work_factory=concrete_factory,
        uuid_factory=uuid_factory,
        clock=clock,
    )
    application.add_middleware(CanonicalCommandMiddleware)
    application.add_exception_handler(
        RequestValidationError,
        canonical_validation_exception_handler,
    )
    dispatch_orchestrator = DispatchOrchestrator(
        unit_of_work_factory=concrete_factory,
        stage=DeterministicAnalyzeStage(),
        uuid_factory=uuid_factory,
        clock=clock,
    )
    application.include_router(create_v1_router(command, dispatch_orchestrator))
    application.include_router(legacy_router)

    @application.middleware("http")
    async def require_login(request: Request, call_next):
        path = request.url.path
        if path in PUBLIC_PATHS:
            if path == "/login" and request_is_authenticated(request):
                return RedirectResponse("/", status_code=303)
            return await call_next(request)
        if not request_is_authenticated(request):
            return unauthenticated_response(request)
        return await call_next(request)

    @application.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(FRONTEND_ROOT / "index.html", media_type="text/html")

    @application.get("/login", include_in_schema=False)
    async def login_page() -> FileResponse:
        return FileResponse(FRONTEND_ROOT / "login.html", media_type="text/html")

    @application.post("/auth/login", include_in_schema=False)
    async def login(request: Request):
        username, password = await read_login_credentials(request)
        if not credentials_are_valid(username, password):
            accept = request.headers.get("accept", "")
            content_type = request.headers.get("content-type", "")
            if "application/json" in accept or "application/json" in content_type:
                return JSONResponse({"error": "invalid_credentials"}, status_code=401)
            return RedirectResponse("/login?error=1", status_code=303)

        accept = request.headers.get("accept", "")
        content_type = request.headers.get("content-type", "")
        if "application/json" in accept or "application/json" in content_type:
            response = JSONResponse({"authenticated": True, "username": username})
        else:
            response = RedirectResponse("/", status_code=303)
        attach_session_cookie(response, username)
        return response

    @application.get("/auth/session", include_in_schema=False)
    async def session() -> dict[str, bool]:
        return {"authenticated": True}

    @application.post("/auth/logout", include_in_schema=False)
    async def logout() -> JSONResponse:
        response = JSONResponse({"authenticated": False})
        clear_session_cookie(response)
        return response

    @application.get("/index.css", include_in_schema=False)
    async def stylesheet() -> FileResponse:
        return FileResponse(FRONTEND_ROOT / "index.css", media_type="text/css")

    @application.get("/main.js", include_in_schema=False)
    async def javascript() -> FileResponse:
        return FileResponse(
            FRONTEND_ROOT / "main.js",
            media_type="application/javascript",
        )

    return application


app = create_app()
