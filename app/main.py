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
from pydantic import BaseModel, ConfigDict, StrictBool

from app.auth import (
    DuplicateUsernameError,
    InvalidUserInputError,
    LastAdminError,
    LoginPayloadTooLarge,
    UserNotFoundError,
    attach_session_cookie_for_user,
    authenticate_user,
    clear_session_cookie,
    create_user,
    load_idempotency_record,
    current_session,
    list_users,
    read_login_credentials,
    request_is_authenticated,
    request_is_admin,
    request_hash,
    serialize_user,
    store_idempotency_record,
    unauthenticated_response,
    update_user,
)
from app.adapters.persistence.database import resolve_database_path
from app.adapters.persistence.unit_of_work import SqliteUnitOfWorkFactory
from app.adapters.legacy.compatibility import configure_database_path
from app.adapters.legacy.compatibility import router as legacy_router
from app.api.v1.errors import canonical_validation_exception_handler
from app.api.v1.middleware import CanonicalCommandMiddleware
from app.api.v1.router import create_v1_router
from app.application.commands.create_work_order import CreateWorkOrder
from app.application.commands.execute_dispatch_run import DispatchOrchestrator
from app.adapters.stages.ollama_analyze import build_analyze_stage_from_environment
from app.application.ports.persistence import UnitOfWorkFactory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
PUBLIC_PATHS = {
    "/healthz",
    "/login",
    "/auth/login",
    "/auth/forgot-password",
    "/index.css",
}


class AdminCreateUserPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    display_name: str
    role: str
    password: str
    is_active: StrictBool = True


class AdminUpdateUserPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = None
    role: str | None = None
    is_active: StrictBool | None = None
    password: str | None = None


def _payload_dict(payload: BaseModel) -> dict[str, object]:
    return payload.model_dump(exclude_none=True)


def _replay_or_conflict(
    *,
    request: Request,
    route: str,
    payload: dict[str, object],
    database_path: str | Path,
) -> JSONResponse | None:
    key = request.headers.get("idempotency-key", "")
    if not key:
        return None
    loaded = load_idempotency_record(
        route=route,
        idempotency_key=key,
        request_hash_value=request_hash(payload),
        database_path=database_path,
    )
    if loaded is None:
        return None
    if loaded == "conflict":
        return JSONResponse({"error": "idempotency_conflict"}, status_code=409)
    status_code, body = loaded
    return JSONResponse(body, status_code=status_code)


def _store_replayable_response(
    *,
    request: Request,
    route: str,
    payload: dict[str, object],
    status_code: int,
    body: dict[str, object],
    database_path: str | Path,
) -> None:
    key = request.headers.get("idempotency-key", "")
    if not key:
        return
    store_idempotency_record(
        route=route,
        idempotency_key=key,
        request_hash_value=request_hash(payload),
        response_status=status_code,
        response_body=body,
        database_path=database_path,
    )


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
    auth_database_path = resolve_database_path(database_path)
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
        stage=build_analyze_stage_from_environment(),
        uuid_factory=uuid_factory,
        clock=clock,
    )
    application.include_router(create_v1_router(command, dispatch_orchestrator))
    configure_database_path(auth_database_path)
    application.include_router(legacy_router)

    @application.middleware("http")
    async def require_login(request: Request, call_next):
        path = request.url.path
        if path in PUBLIC_PATHS:
            if path == "/login" and request_is_authenticated(request, auth_database_path):
                return RedirectResponse("/", status_code=303)
            return await call_next(request)
        if not request_is_authenticated(request, auth_database_path):
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
        try:
            username, password = await read_login_credentials(request)
        except LoginPayloadTooLarge:
            return JSONResponse({"error": "payload_too_large"}, status_code=413)
        user = authenticate_user(username, password, auth_database_path)
        if user is None:
            accept = request.headers.get("accept", "")
            content_type = request.headers.get("content-type", "")
            if "application/json" in accept or "application/json" in content_type:
                return JSONResponse({"error": "invalid_credentials"}, status_code=401)
            return RedirectResponse("/login?error=1", status_code=303)

        accept = request.headers.get("accept", "")
        content_type = request.headers.get("content-type", "")
        if "application/json" in accept or "application/json" in content_type:
            response = JSONResponse(
                {
                    "authenticated": True,
                    "username": user.username,
                    "role": user.role,
                    "display_name": user.display_name,
                }
            )
        else:
            response = RedirectResponse("/", status_code=303)
        attach_session_cookie_for_user(response, user)
        return response

    @application.get("/auth/session", include_in_schema=False)
    async def session(request: Request) -> dict[str, object]:
        session_data = current_session(request, auth_database_path)
        if session_data is None:
            return {"authenticated": False}
        return {
            "authenticated": True,
            "username": session_data.username,
            "role": session_data.role,
            "user_id": session_data.user_id,
        }

    @application.post("/auth/forgot-password", include_in_schema=False)
    async def forgot_password() -> dict[str, str]:
        return {
            "status": "manual_recovery_required",
            "message": "Solicita a un administrador que restablezca tu clave.",
        }

    @application.post("/auth/logout", include_in_schema=False)
    async def logout() -> JSONResponse:
        response = JSONResponse({"authenticated": False})
        clear_session_cookie(response)
        return response

    @application.get("/api/v1/admin/users", include_in_schema=False)
    async def admin_list_users(request: Request) -> JSONResponse:
        if not request_is_admin(request, auth_database_path):
            return JSONResponse({"error": "admin_required"}, status_code=403)
        return JSONResponse(
            {"users": [serialize_user(user) for user in list_users(auth_database_path)]}
        )

    @application.post("/api/v1/admin/users", include_in_schema=False)
    async def admin_create_user(
        request: Request,
        payload: AdminCreateUserPayload,
    ) -> JSONResponse:
        if not request_is_admin(request, auth_database_path):
            return JSONResponse({"error": "admin_required"}, status_code=403)
        payload_dict = _payload_dict(payload)
        replay = _replay_or_conflict(
            request=request,
            route="/api/v1/admin/users",
            payload=payload_dict,
            database_path=auth_database_path,
        )
        if replay is not None:
            return replay
        try:
            user = create_user(
                username=payload.username,
                display_name=payload.display_name,
                role=payload.role,
                password=payload.password,
                is_active=payload.is_active,
                database_path=auth_database_path,
            )
        except DuplicateUsernameError:
            return JSONResponse({"error": "username_exists"}, status_code=409)
        except InvalidUserInputError as error:
            return JSONResponse(
                {"error": "invalid_user", "message": str(error)},
                status_code=422,
            )
        body = {"user": serialize_user(user)}
        _store_replayable_response(
            request=request,
            route="/api/v1/admin/users",
            payload=payload_dict,
            status_code=201,
            body=body,
            database_path=auth_database_path,
        )
        return JSONResponse(body, status_code=201)

    @application.patch("/api/v1/admin/users/{user_id}", include_in_schema=False)
    async def admin_update_user(
        user_id: str,
        request: Request,
        payload: AdminUpdateUserPayload,
    ) -> JSONResponse:
        if not request_is_admin(request, auth_database_path):
            return JSONResponse({"error": "admin_required"}, status_code=403)
        payload_dict = _payload_dict(payload)
        route = f"/api/v1/admin/users/{user_id}"
        replay = _replay_or_conflict(
            request=request,
            route=route,
            payload=payload_dict,
            database_path=auth_database_path,
        )
        if replay is not None:
            return replay
        try:
            user = update_user(
                user_id,
                display_name=payload.display_name,
                role=payload.role,
                is_active=payload.is_active,
                password=payload.password,
                database_path=auth_database_path,
            )
        except UserNotFoundError:
            return JSONResponse({"error": "user_not_found"}, status_code=404)
        except LastAdminError:
            return JSONResponse({"error": "last_admin_required"}, status_code=409)
        except InvalidUserInputError as error:
            return JSONResponse(
                {"error": "invalid_user", "message": str(error)},
                status_code=422,
            )
        body = {"user": serialize_user(user)}
        _store_replayable_response(
            request=request,
            route=route,
            payload=payload_dict,
            status_code=200,
            body=body,
            database_path=auth_database_path,
        )
        return JSONResponse(body)

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
