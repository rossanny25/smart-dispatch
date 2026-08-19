"""Mechanical FastAPI relocation of the original ``server.py`` API behavior."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
import sqlite3
from typing import Any
import unicodedata
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.auth import (
    load_idempotency_record,
    request_hash,
    request_is_admin,
    store_idempotency_record,
)
from app.adapters.persistence.database import (
    PROJECT_ROOT,
    connect_sqlite,
    resolve_database_path,
)


router = APIRouter(include_in_schema=False)
LEARNING_STORE_PATH_ENV = "SMART_DISPATCH_LEARNING_STORE_PATH"
SEED_DATA_DIR = PROJECT_ROOT / "data" / "seeds"
SEED_TECHNICIANS_PATH = SEED_DATA_DIR / "technicians.json"
SEED_ORDERS_PATH = SEED_DATA_DIR / "orders.json"
SEED_LEARNING_STORE_PATH = PROJECT_ROOT / "data" / "learning_store.json"
DEFAULT_LEARNING_STORE_PATH = PROJECT_ROOT / "data" / "learning_store.runtime.json"
ALLOWED_TECHNICIAN_STATUSES = {"disponible", "ocupado", "fuera_servicio"}
KNOWN_SERVICE_TERMS = {
    "agua",
    "aire",
    "averia",
    "avería",
    "bano",
    "baño",
    "caldera",
    "cano",
    "caño",
    "climatiz",
    "corte",
    "electric",
    "fibra",
    "frio",
    "frío",
    "fuga",
    "gas",
    "hvac",
    "internet",
    "inund",
    "luz",
    "plomer",
    "red",
    "regulador",
    "tension",
    "tensión",
    "termica",
    "térmica",
    "urgente",
}
TECHNICIAN_CREATE_FIELDS = {
    "id",
    "name",
    "status",
    "zone",
    "certifications",
    "shift",
    "active_workload_hours",
    "rating",
    "ppe",
    "gps_coordinates",
}
TECHNICIAN_UPDATE_FIELDS = TECHNICIAN_CREATE_FIELDS - {"id"}
_database_path_override: Path | None = None


def load_seed_list(path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Seed data could not be loaded: {path}") from error
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise RuntimeError(f"Seed data must be a JSON array of objects: {path}")
    return value


technicians = load_seed_list(SEED_TECHNICIANS_PATH)
orders = load_seed_list(SEED_ORDERS_PATH)


ZONE_DISTANCES = {
    "Palermo": {"Palermo": 2, "Belgrano": 4, "Almagro": 5, "Caballito": 6, "Centro": 7},
    "Centro": {"Centro": 1.5, "Almagro": 4, "Palermo": 7, "Caballito": 7, "Belgrano": 9},
    "Belgrano": {"Belgrano": 2, "Palermo": 4, "Caballito": 7, "Almagro": 8, "Centro": 9},
    "Almagro": {"Almagro": 1.8, "Caballito": 3, "Centro": 4, "Palermo": 5, "Belgrano": 8},
    "Caballito": {"Caballito": 2, "Almagro": 3, "Palermo": 6, "Centro": 7, "Belgrano": 7},
}


class TechnicianValidationError(ValueError):
    """Technician payload failed validation."""


class TechnicianStoreUnavailable(RuntimeError):
    """Technician SQLite store is not available for mutation."""


def configure_database_path(database_path: str | Path | None = None) -> None:
    global _database_path_override
    _database_path_override = resolve_database_path(database_path)


def _database_path() -> Path:
    return _database_path_override or resolve_database_path()


def _connect() -> sqlite3.Connection:
    connection = connect_sqlite(_database_path())
    connection.row_factory = sqlite3.Row
    return connection


def _technician_table_exists(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = 'service_technicians'"
    ).fetchone()
    return row is not None


def _visits_table_exists(connection: sqlite3.Connection) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = 'service_visits'"
    ).fetchone()
    return row is not None


def resolve_learning_store_path() -> Path:
    selected = os.environ.get(LEARNING_STORE_PATH_ENV)
    if selected is None:
        return DEFAULT_LEARNING_STORE_PATH
    path = Path(selected)
    return path if path.is_absolute() else PROJECT_ROOT / path


def resolve_learning_read_path() -> Path:
    runtime_path = resolve_learning_store_path()
    if (
        runtime_path == DEFAULT_LEARNING_STORE_PATH
        and not runtime_path.exists()
        and SEED_LEARNING_STORE_PATH.exists()
    ):
        return SEED_LEARNING_STORE_PATH
    return runtime_path


def _seed_learnings() -> list[dict[str, Any]]:
    updated_at = datetime.now(UTC).isoformat()
    return [
        {
            "key": "tech_efficiency_tech_02_networks",
            "type": "calibracion_tiempo",
            "learning_content": {
                "description": (
                    "Sofía Torres resuelve incidencias de Fibra Óptica un 15% "
                    "más rápido que la media general."
                ),
                "parameters": {
                    "technician_id": "tech_02",
                    "skill": "Fibra Óptica",
                    "modifier": 0.85,
                },
            },
            "confidence": 0.92,
            "updated_at": updated_at,
        },
        {
            "key": "preference_palermo_gas",
            "type": "preferencia_usuario",
            "learning_content": {
                "description": (
                    "Preferencia del despachador para asignar a Carlos Rodríguez "
                    "en trabajos de Gas en Palermo."
                ),
                "parameters": {
                    "technician_id": "tech_01",
                    "zone": "Palermo",
                    "skill": "Gasista Matriculado",
                },
            },
            "confidence": 0.85,
            "updated_at": updated_at,
        },
    ]


def init_storage() -> None:
    path = resolve_learning_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        if path == DEFAULT_LEARNING_STORE_PATH and SEED_LEARNING_STORE_PATH.exists():
            path.write_bytes(SEED_LEARNING_STORE_PATH.read_bytes())
        else:
            path.write_text(
                json.dumps(_seed_learnings(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )


def read_learnings() -> list[dict[str, Any]]:
    try:
        return json.loads(resolve_learning_read_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def write_learnings(learnings: list[dict[str, Any]]) -> None:
    resolve_learning_store_path().write_text(
        json.dumps(learnings, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _json_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
        return [part for part in parts if part]
    if not isinstance(value, list):
        raise TechnicianValidationError("El campo debe ser una lista o texto separado por comas.")
    if any(not isinstance(item, str) for item in value):
        raise TechnicianValidationError("Los valores de lista deben ser texto.")
    values = [str(item).strip() for item in value]
    return [item for item in values if item]


def _decimal_text(value: Any, *, field: str, minimum: Decimal, maximum: Decimal) -> str:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise TechnicianValidationError(f"{field} debe ser numérico.") from error
    if not number.is_finite():
        raise TechnicianValidationError(f"{field} debe ser finito.")
    if number < minimum or number > maximum:
        raise TechnicianValidationError(f"{field} debe estar entre {minimum} y {maximum}.")
    return format(number.quantize(Decimal("0.1")), "f")


def _time_text(value: Any, *, field: str) -> str:
    text = str(value or "").strip()
    if not re.fullmatch(r"[0-2][0-9]:[0-5][0-9]", text):
        raise TechnicianValidationError(f"{field} debe tener formato HH:MM.")
    hour = int(text.split(":", 1)[0])
    if hour > 23:
        raise TechnicianValidationError(f"{field} debe tener formato HH:MM.")
    return text


def _gps_payload(value: Any) -> dict[str, float]:
    if value is None:
        return {"lat": 0.0, "lng": 0.0}
    if not isinstance(value, dict):
        raise TechnicianValidationError("gps_coordinates debe ser un objeto.")
    try:
        lat = float(value.get("lat", 0))
        lng = float(value.get("lng", 0))
    except (TypeError, ValueError) as error:
        raise TechnicianValidationError("GPS debe contener lat/lng numéricos.") from error
    if lat < -90 or lat > 90 or lng < -180 or lng > 180:
        raise TechnicianValidationError("GPS está fuera de rango.")
    return {"lat": lat, "lng": lng}


def _validate_technician_payload(
    payload: dict[str, Any],
    *,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    allowed_fields = (
        TECHNICIAN_UPDATE_FIELDS | {"id"} if existing else TECHNICIAN_CREATE_FIELDS
    )
    unknown_fields = set(payload) - allowed_fields
    if unknown_fields:
        raise TechnicianValidationError(
            "Campos no permitidos: " + ", ".join(sorted(unknown_fields))
        )
    source = existing or {}
    supplied_id = payload.get("id", source.get("id", f"tech_{uuid4().hex[:8]}"))
    technician_id = str(supplied_id).strip()
    if not re.fullmatch(r"tech_[A-Za-z0-9_-]{1,64}", technician_id):
        raise TechnicianValidationError("id de técnico inválido.")
    name = str(payload.get("name", source.get("name", ""))).strip()
    if len(name) < 2 or len(name) > 120:
        raise TechnicianValidationError("El nombre debe tener entre 2 y 120 caracteres.")
    zone = str(payload.get("zone", source.get("zone", ""))).strip()
    if len(zone) < 2 or len(zone) > 80:
        raise TechnicianValidationError("La zona es requerida.")
    status = str(payload.get("status", source.get("status", "disponible"))).strip()
    if status not in ALLOWED_TECHNICIAN_STATUSES:
        raise TechnicianValidationError("Estado de técnico inválido.")
    shift = payload.get("shift", source.get("shift", {}))
    if not isinstance(shift, dict):
        raise TechnicianValidationError("El turno debe tener inicio y fin.")
    return {
        "id": technician_id,
        "name": name,
        "status": status,
        "zone": zone,
        "certifications": _json_list(
            payload.get("certifications", source.get("certifications", []))
        ),
        "shift": {
            "start": _time_text(shift.get("start"), field="Inicio de turno"),
            "end": _time_text(shift.get("end"), field="Fin de turno"),
        },
        "active_workload_hours": float(
            _decimal_text(
                payload.get(
                    "active_workload_hours",
                    source.get("active_workload_hours", 0),
                ),
                field="Carga diaria",
                minimum=Decimal("0"),
                maximum=Decimal("16"),
            )
        ),
        "rating": float(
            _decimal_text(
                payload.get("rating", source.get("rating", 4.5)),
                field="Calificación",
                minimum=Decimal("0"),
                maximum=Decimal("5"),
            )
        ),
        "ppe": _json_list(payload.get("ppe", source.get("ppe", []))),
        "gps_coordinates": _gps_payload(
            payload.get("gps_coordinates", source.get("gps_coordinates"))
        ),
    }


def _row_to_technician(row: sqlite3.Row) -> dict[str, Any]:
    certifications = json.loads(str(row["certifications_json"]))
    ppe = json.loads(str(row["ppe_json"]))
    gps = json.loads(str(row["gps_json"]))
    if (
        not isinstance(certifications, list)
        or not isinstance(ppe, list)
        or not isinstance(gps, dict)
    ):
        raise RuntimeError("Persisted technician row is corrupt.")
    return {
        "id": str(row["id"]),
        "name": str(row["name"]),
        "status": str(row["status"]),
        "zone": str(row["zone"]),
        "certifications": certifications,
        "shift": {
            "start": str(row["shift_start"]),
            "end": str(row["shift_end"]),
        },
        "active_workload_hours": float(row["active_workload_hours"]),
        "rating": float(row["rating"]),
        "ppe": ppe,
        "gps_coordinates": gps,
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def _technician_values(technician: dict[str, Any], now: str) -> tuple[object, ...]:
    return (
        technician["id"],
        technician["name"],
        technician["status"],
        technician["zone"],
        json.dumps(technician["certifications"], ensure_ascii=False, sort_keys=True),
        technician["shift"]["start"],
        technician["shift"]["end"],
        float(technician["active_workload_hours"]),
        float(technician["rating"]),
        json.dumps(technician.get("ppe", []), ensure_ascii=False, sort_keys=True),
        json.dumps(
            technician.get("gps_coordinates", {"lat": 0.0, "lng": 0.0}),
            ensure_ascii=False,
            sort_keys=True,
        ),
        now,
        now,
    )


def bootstrap_service_technicians(
    database_path: str | Path | None = None,
) -> None:
    if database_path is not None:
        configure_database_path(database_path)
    with _connect() as connection:
        if not _technician_table_exists(connection):
            raise RuntimeError("service_technicians table is not available.")
        count = connection.execute("SELECT count(*) FROM service_technicians").fetchone()[0]
        if count:
            return
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        for item in load_seed_list(SEED_TECHNICIANS_PATH):
            technician = _validate_technician_payload(item)
            connection.execute(
                """
                INSERT INTO service_technicians (
                    id, name, status, zone, certifications_json, shift_start,
                    shift_end, active_workload_hours, rating, ppe_json, gps_json,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _technician_values(technician, now),
            )


def list_service_technicians() -> list[dict[str, Any]]:
    with _connect() as connection:
        if not _technician_table_exists(connection):
            return [item.copy() for item in technicians]
        rows = connection.execute(
            """
            SELECT * FROM service_technicians
            ORDER BY name ASC
            """
        ).fetchall()
    return [_row_to_technician(row) for row in rows]


def get_service_technician(technician_id: str) -> dict[str, Any] | None:
    for technician in list_service_technicians():
        if technician["id"] == technician_id:
            return technician
    return None


def create_service_technician(payload: dict[str, Any]) -> dict[str, Any]:
    technician = _validate_technician_payload(payload)
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    try:
        with _connect() as connection:
            if not _technician_table_exists(connection):
                raise TechnicianStoreUnavailable("service_technicians table is not available.")
            connection.execute(
                """
                INSERT INTO service_technicians (
                    id, name, status, zone, certifications_json, shift_start,
                    shift_end, active_workload_hours, rating, ppe_json, gps_json,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _technician_values(technician, now),
            )
    except sqlite3.IntegrityError as error:
        raise TechnicianValidationError("Ya existe un técnico con ese nombre o id.") from error
    created = get_service_technician(technician["id"])
    if created is None:
        raise TechnicianValidationError("No se pudo guardar el técnico.")
    return created


def update_service_technician(
    technician_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    existing = get_service_technician(technician_id)
    if existing is None:
        raise KeyError(technician_id)
    technician = _validate_technician_payload(
        {**payload, "id": technician_id},
        existing=existing,
    )
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    try:
        with _connect() as connection:
            if not _technician_table_exists(connection):
                raise TechnicianStoreUnavailable("service_technicians table is not available.")
            connection.execute(
                """
                UPDATE service_technicians
                SET name = ?, status = ?, zone = ?, certifications_json = ?,
                    shift_start = ?, shift_end = ?, active_workload_hours = ?,
                    rating = ?, ppe_json = ?, gps_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    technician["name"],
                    technician["status"],
                    technician["zone"],
                    json.dumps(
                        technician["certifications"],
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    technician["shift"]["start"],
                    technician["shift"]["end"],
                    float(technician["active_workload_hours"]),
                    float(technician["rating"]),
                    json.dumps(technician["ppe"], ensure_ascii=False, sort_keys=True),
                    json.dumps(
                        technician["gps_coordinates"],
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    now,
                    technician_id,
                ),
            )
    except sqlite3.IntegrityError as error:
        raise TechnicianValidationError("Ya existe un técnico con ese nombre.") from error
    updated = get_service_technician(technician_id)
    if updated is None:
        raise KeyError(technician_id)
    return updated


def reset_service_technicians() -> None:
    with _connect() as connection:
        if not _technician_table_exists(connection):
            technicians[:] = load_seed_list(SEED_TECHNICIANS_PATH)
            return
        connection.execute("DELETE FROM service_technicians")
    bootstrap_service_technicians()


def _row_to_visit(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "order_id": str(row["order_id"]),
        "technician_id": str(row["technician_id"]),
        "technician_name": str(row["technician_name"]),
        "client": str(row["client"]),
        "address": str(row["address"]),
        "zone": str(row["zone"]),
        "category": str(row["category"]),
        "status": str(row["status"]),
        "scheduled_start_at": str(row["scheduled_start_at"]),
        "scheduled_end_at": str(row["scheduled_end_at"]),
        "duration_minutes": int(row["duration_minutes"]),
        "feedback_comment": str(row["feedback_comment"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def _select_visit_by_order(
    connection: sqlite3.Connection,
    order_id: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT
            v.id,
            v.order_id,
            v.technician_id,
            COALESCE(t.name, v.technician_name) AS technician_name,
            v.client,
            v.address,
            v.zone,
            v.category,
            v.status,
            v.scheduled_start_at,
            v.scheduled_end_at,
            v.duration_minutes,
            v.feedback_comment,
            v.created_at,
            v.updated_at
        FROM service_visits AS v
        LEFT JOIN service_technicians AS t ON t.id = v.technician_id
        WHERE v.order_id = ?
        """,
        (order_id,),
    ).fetchone()


def find_service_visit_by_order(order_id: str) -> dict[str, Any] | None:
    with _connect() as connection:
        if not _visits_table_exists(connection):
            return None
        row = _select_visit_by_order(connection, order_id)
    return _row_to_visit(row) if row is not None else None


def list_service_visits() -> list[dict[str, Any]]:
    with _connect() as connection:
        if not _visits_table_exists(connection):
            return []
        rows = connection.execute(
            """
            SELECT
                v.id,
                v.order_id,
                v.technician_id,
                COALESCE(t.name, v.technician_name) AS technician_name,
                v.client,
                v.address,
                v.zone,
                v.category,
                v.status,
                v.scheduled_start_at,
                v.scheduled_end_at,
                v.duration_minutes,
                v.feedback_comment,
                v.created_at,
                v.updated_at
            FROM service_visits AS v
            LEFT JOIN service_technicians AS t ON t.id = v.technician_id
            ORDER BY v.scheduled_start_at DESC, v.created_at DESC
            """
        ).fetchall()
    return [_row_to_visit(row) for row in rows]


def create_service_visit(
    *,
    order: dict[str, Any],
    technician: dict[str, Any],
    duration_minutes: int,
    feedback_comment: str,
) -> dict[str, Any]:
    minutes = max(1, min(1440, int(duration_minutes or 90)))
    started_at = datetime.now(UTC)
    ended_at = started_at + timedelta(minutes=minutes)
    now = started_at.isoformat().replace("+00:00", "Z")
    visit = {
        "id": f"visit_{uuid4().hex[:10]}",
        "order_id": str(order["id"]),
        "technician_id": str(technician["id"]),
        "technician_name": str(technician["name"]),
        "client": str(order.get("client") or "Cliente"),
        "address": str(order.get("address") or ""),
        "zone": str(order.get("zone") or technician.get("zone") or ""),
        "category": str(order.get("structured_data", {}).get("category") or "Servicio"),
        "status": "completada",
        "scheduled_start_at": started_at.isoformat().replace("+00:00", "Z"),
        "scheduled_end_at": ended_at.isoformat().replace("+00:00", "Z"),
        "duration_minutes": minutes,
        "feedback_comment": feedback_comment.strip(),
        "created_at": now,
        "updated_at": now,
    }
    with _connect() as connection:
        if not _visits_table_exists(connection):
            raise RuntimeError("service_visits table is unavailable")
        existing = _select_visit_by_order(connection, visit["order_id"])
        if existing is not None:
            return _row_to_visit(existing)
        try:
            connection.execute(
                """
                INSERT INTO service_visits (
                    id, order_id, technician_id, technician_name, client, address,
                    zone, category, status, scheduled_start_at, scheduled_end_at,
                    duration_minutes, feedback_comment, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    visit["id"],
                    visit["order_id"],
                    visit["technician_id"],
                    visit["technician_name"],
                    visit["client"],
                    visit["address"],
                    visit["zone"],
                    visit["category"],
                    visit["status"],
                    visit["scheduled_start_at"],
                    visit["scheduled_end_at"],
                    visit["duration_minutes"],
                    visit["feedback_comment"],
                    visit["created_at"],
                    visit["updated_at"],
                ),
            )
        except sqlite3.IntegrityError:
            existing = _select_visit_by_order(connection, visit["order_id"])
            if existing is not None:
                return _row_to_visit(existing)
            raise
    return visit


def reset_service_visits() -> None:
    with _connect() as connection:
        if _visits_table_exists(connection):
            connection.execute("DELETE FROM service_visits")


def _looks_like_actionable_order(raw_text: str, address: str) -> bool:
    text = _normalize_text(raw_text)
    normalized = re.sub(r"[^a-z0-9 ]+", " ", text)
    words = [word for word in normalized.split() if len(word) >= 3]
    has_known_term = any(
        word in KNOWN_SERVICE_TERMS
        or any(word.startswith(term) for term in KNOWN_SERVICE_TERMS if len(term) >= 5)
        for word in words
    )
    has_sentence_shape = len(words) >= 2 and len(set(words)) >= 2
    has_address_signal = bool(re.search(r"\d", address)) and len(address.strip()) >= 8
    return has_known_term and has_sentence_shape and has_address_signal


def _normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFD", value.strip().lower())
    return "".join(character for character in decomposed if unicodedata.category(character) != "Mn")


def _replay_or_conflict(
    request: Request,
    route: str,
    payload: dict[str, Any],
) -> JSONResponse | None:
    key = request.headers.get("idempotency-key", "")
    if not key:
        return JSONResponse({"error": "idempotency_key_required"}, status_code=422)
    loaded = load_idempotency_record(
        route=route,
        idempotency_key=key,
        request_hash_value=request_hash(payload),
        database_path=_database_path(),
    )
    if loaded is None:
        return None
    if loaded == "conflict":
        return JSONResponse({"error": "idempotency_conflict"}, status_code=409)
    status_code, body = loaded
    return JSONResponse(body, status_code=status_code)


def _store_replayable_response(
    request: Request,
    route: str,
    payload: dict[str, Any],
    status_code: int,
    body: dict[str, Any],
) -> None:
    store_idempotency_record(
        route=route,
        idempotency_key=request.headers.get("idempotency-key", ""),
        request_hash_value=request_hash(payload),
        response_status=status_code,
        response_body=body,
        database_path=_database_path(),
    )


def get_distance(zone_a: str, zone_b: str) -> float:
    return ZONE_DISTANCES.get(zone_a, {}).get(zone_b, 8.0)


def _shift_hours(technician: dict[str, Any]) -> float | None:
    shift = technician.get("shift", {})
    if not isinstance(shift, dict) or "start" not in shift or "end" not in shift:
        return None
    start = str(shift["start"])
    end = str(shift["end"])
    try:
        start_hour, start_minute = [int(part) for part in start.split(":", 1)]
        end_hour, end_minute = [int(part) for part in end.split(":", 1)]
    except ValueError:
        return None
    start_total = start_hour + start_minute / 60
    end_total = end_hour + end_minute / 60
    if end_total <= start_total:
        end_total += 24
    return end_total - start_total


def _rule_check(key: str, label: str, passed: bool, detail: str) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "status": "pass" if passed else "fail",
        "detail": detail,
    }


def build_hard_rule_checks(
    technician: dict[str, Any],
    order: dict[str, Any],
    travel_minutes: float,
) -> tuple[list[dict[str, Any]], list[str], float]:
    required = order["structured_data"].get("required_skills", [])
    required_ppe = order["structured_data"].get("required_ppe", order.get("required_ppe", []))
    certifications = technician.get("certifications", [])
    ppe = technician.get("ppe", [])
    missing_skills = [skill for skill in required if skill not in certifications]
    missing_ppe = [item for item in required_ppe if item not in ppe]
    potential_hours = technician["active_workload_hours"] + (
        travel_minutes + 90
    ) / 60
    shift_hours = _shift_hours(technician)

    checks = [
        _rule_check(
            "availability",
            "Disponibilidad",
            technician.get("status") == "disponible",
            (
                "Disponible para despacho"
                if technician.get("status") == "disponible"
                else f"Estado actual: {technician.get('status', 'desconocido')}"
            ),
        ),
        _rule_check(
            "certifications",
            "Certificaciones",
            not missing_skills,
            (
                "Cumple certificaciones requeridas"
                if not missing_skills
                else "Faltan: " + ", ".join(missing_skills)
            ),
        ),
        _rule_check(
            "shift",
            "Turno",
            shift_hours is not None and shift_hours >= 8,
            (
                f"Turno configurado de {shift_hours:.1f}hs"
                if shift_hours is not None
                else "Turno ausente o inválido"
            ),
        ),
        _rule_check(
            "workload",
            "Jornada máxima",
            potential_hours <= 8,
            f"Jornada proyectada: {potential_hours:.1f}hs",
        ),
        _rule_check(
            "driving_limit",
            "Límite de conducción",
            travel_minutes <= 240,
            f"Viaje estimado: {int(travel_minutes)} min",
        ),
        _rule_check(
            "ppe",
            "EPP requerido",
            not missing_ppe,
            (
                "EPP requerido disponible"
                if required_ppe and not missing_ppe
                else "Sin EPP especial requerido en el escenario demo"
                if not required_ppe
                else "Falta EPP: " + ", ".join(missing_ppe)
            ),
        ),
    ]
    rejection_reasons = [
        check["detail"] for check in checks if check["status"] == "fail"
    ]
    return checks, rejection_reasons, potential_hours


def build_confidence_evidence(
    recommended: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    rejected_count = sum(
        1 for candidate in candidates if candidate["validation_status"] == "rechazado"
    )
    value = 0.84
    factors = ["Reglas duras completas para el técnico recomendado"]
    if recommended.get("gps_signal") == "offline":
        value -= 0.15
        factors.append("Señal GPS offline reduce la certeza contextual")
    if rejected_count:
        value -= 0.05
        factors.append(f"{rejected_count} técnicos descartados por reglas duras")
    if recommended.get("memory_bonus", 0) > 0:
        value += 0.04
        factors.append("Existe evidencia histórica aplicable")
    value = max(0.45, min(0.95, value))
    label = "alta" if value >= 0.75 else "media" if value >= 0.6 else "baja"
    return {
        "value": round(value, 2),
        "label": label,
        "factors": factors,
    }


async def parse_body(request: Request) -> dict[str, Any] | None:
    try:
        value = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return value if isinstance(value, dict) else None


@router.get("/api/technicians")
async def list_technicians() -> list[dict[str, Any]]:
    return list_service_technicians()


@router.post("/api/technicians")
async def create_technician(request: Request) -> JSONResponse:
    if not request_is_admin(request, _database_path()):
        return JSONResponse({"error": "admin_required"}, status_code=403)
    body = await parse_body(request)
    if body is None:
        return JSONResponse({"error": "JSON inválido"}, status_code=400)
    replay = _replay_or_conflict(request, "/api/technicians", body)
    if replay is not None:
        return replay
    try:
        technician = create_service_technician(body)
    except TechnicianStoreUnavailable as error:
        return JSONResponse({"error": "technician_store_unavailable", "message": str(error)}, status_code=503)
    except TechnicianValidationError as error:
        return JSONResponse({"error": "technician_invalid", "message": str(error)}, status_code=422)
    response_body = {"technician": technician}
    _store_replayable_response(request, "/api/technicians", body, 201, response_body)
    return JSONResponse(response_body, status_code=201)


@router.patch("/api/technicians/{technician_id}")
async def update_technician(technician_id: str, request: Request) -> JSONResponse:
    if not request_is_admin(request, _database_path()):
        return JSONResponse({"error": "admin_required"}, status_code=403)
    body = await parse_body(request)
    if body is None:
        return JSONResponse({"error": "JSON inválido"}, status_code=400)
    route = f"/api/technicians/{technician_id}"
    replay = _replay_or_conflict(request, route, body)
    if replay is not None:
        return replay
    try:
        technician = update_service_technician(technician_id, body)
    except KeyError:
        return JSONResponse({"error": "technician_not_found"}, status_code=404)
    except TechnicianStoreUnavailable as error:
        return JSONResponse({"error": "technician_store_unavailable", "message": str(error)}, status_code=503)
    except TechnicianValidationError as error:
        return JSONResponse({"error": "technician_invalid", "message": str(error)}, status_code=422)
    response_body = {"technician": technician}
    _store_replayable_response(request, route, body, 200, response_body)
    return JSONResponse(response_body)


@router.get("/api/orders")
async def list_orders() -> list[dict[str, Any]]:
    return orders


@router.get("/api/memory/learning")
async def list_memory() -> list[dict[str, Any]]:
    return read_learnings()


@router.get("/api/visits")
async def list_visits() -> list[dict[str, Any]]:
    return list_service_visits()


@router.post("/api/reset")
async def reset_simulation(request: Request) -> JSONResponse:
    if not request_is_admin(request, _database_path()):
        return JSONResponse({"error": "admin_required"}, status_code=403)
    init_storage()
    reset_service_visits()
    reset_service_technicians()
    orders[:] = load_seed_list(SEED_ORDERS_PATH)
    if SEED_LEARNING_STORE_PATH.exists():
        write_learnings(load_seed_list(SEED_LEARNING_STORE_PATH))
    else:
        write_learnings(_seed_learnings())
    return JSONResponse({"message": "Estado de simulación y memoria restablecidos."})


def classify_order(raw_text: str) -> tuple[str, int, list[str]]:
    text = _normalize_text(raw_text)
    if any(term in text for term in ("gas", "fuga", "caldera")):
        return "Gas", 5 if "fuga" in text else 4, ["Gasista Matriculado"]
    if any(term in text for term in ("luz", "electric", "térmica", "tensión")):
        priority = 4 if any(term in text for term in ("corte", "urgente")) else 3
        return "Electricidad", priority, ["Técnico Electricista A"]
    if any(term in text for term in ("internet", "enlace", "fibra", "red")):
        skills = ["Redes WAN"]
        if "fibra" in text:
            skills.append("Fibra Óptica")
        return "Telecomunicaciones", 4 if "urgente" in text else 3, skills
    if any(term in text for term in ("agua", "caño", "inund", "baño", "plomer")):
        return "Plomería", 4, ["Plomero Matriculado"]
    if any(term in text for term in ("aire", "frío", "hvac", "climatiz")):
        return "Climatización", 3, ["Técnico HVAC"]
    return "Mantenimiento", 2, []


@router.post("/api/orders")
async def create_order(request: Request) -> JSONResponse:
    body = await parse_body(request)
    if body is None:
        return JSONResponse({"error": "JSON inválido"}, status_code=400)
    raw_text = body.get("raw_text")
    address = body.get("address")
    zone = body.get("zone")
    if not raw_text or not address or not zone:
        return JSONResponse(
            {"error": "Faltan campos (raw_text, address, zone)"},
            status_code=400,
        )
    if not _looks_like_actionable_order(str(raw_text), str(address)):
        return JSONResponse(
            {
                "error": "Solicitud no entendida",
                "message": (
                    "Describe una avería reconocible e incluye una dirección "
                    "con numeración para poder inferir categoría, habilidad y zona."
                ),
            },
            status_code=422,
        )

    category, priority, required_skills = classify_order(str(raw_text))
    new_order = {
        "id": f"order_{str(int(datetime.now(UTC).timestamp()))[-4:]}",
        "client": "Cliente Solicitante",
        "address": address,
        "zone": zone,
        "raw_text": raw_text,
        "status": "pendiente",
        "created_at": datetime.now(UTC).isoformat(),
        "structured_data": {
            "category": category,
            "subcategory": "Reclamo General",
            "priority": priority,
            "required_skills": required_skills,
        },
    }
    orders.insert(0, new_order)
    return JSONResponse(new_order, status_code=201)


def build_candidates(
    order: dict[str, Any],
    environment: dict[str, Any],
) -> list[dict[str, Any]]:
    learnings = read_learnings()
    candidates: list[dict[str, Any]] = []
    required = order["structured_data"]["required_skills"]
    for technician in list_service_technicians():
        distance_km = get_distance(technician["zone"], order["zone"])
        travel_minutes = distance_km * 4
        if environment.get("traffic") == "congestionado":
            travel_minutes += distance_km * 5
        if environment.get("weather") == "lluvia_extrema":
            travel_minutes += 15
        hard_rule_checks, rejection_reasons, potential_hours = build_hard_rule_checks(
            technician,
            order,
            travel_minutes,
        )
        eligible = not rejection_reasons

        memory_bonus = 0
        memory_notes: list[str] = []
        efficiency = next(
            (
                item
                for item in learnings
                if item["type"] == "calibracion_tiempo"
                and item["learning_content"]["parameters"]["technician_id"]
                == technician["id"]
                and any(skill in technician["certifications"] for skill in required)
            ),
            None,
        )
        if efficiency:
            memory_bonus += 10
            modifier = efficiency["learning_content"]["parameters"]["modifier"]
            memory_notes.append(f"Calibración de eficiencia (coeficiente {modifier}).")
        preference = next(
            (
                item
                for item in learnings
                if item["type"] == "preferencia_usuario"
                and item["learning_content"]["parameters"]["technician_id"]
                == technician["id"]
                and item["learning_content"]["parameters"]["zone"] == order["zone"]
            ),
            None,
        )
        if preference:
            memory_bonus += 10
            memory_notes.append(f"Preferencia en zona {order['zone']}.")

        gps_penalty = 20 if environment.get("gps_signal") == "offline" else 0
        proximity = max(0, 45 - distance_km * 3.5)
        workload = max(0, 35 - technician["active_workload_hours"] * 5)
        score = (
            min(100, max(0, int(50 + proximity + workload + memory_bonus - gps_penalty)))
            if eligible
            else None
        )
        candidates.append(
            {
                "technician_id": technician["id"],
                "name": technician["name"],
                "zone": technician["zone"],
                "score": score,
                "calculated_travel_time_minutes": int(travel_minutes),
                "distance_km": distance_km,
                "active_workload_hours": technician["active_workload_hours"],
                "projected_workload_hours": round(potential_hours, 1),
                "memory_bonus": memory_bonus,
                "memory_justification": (
                    " ".join(memory_notes)
                    if memory_notes
                    else "Sin datos históricos específicos."
                ),
                "gps_signal": environment.get("gps_signal"),
                "eligibility_status": "eligible" if eligible else "rejected",
                "hard_rule_checks": hard_rule_checks,
                "rejection_reasons": rejection_reasons,
            }
        )
    candidates.sort(
        key=lambda candidate: (
            candidate["score"] is not None,
            candidate["score"] or -1,
        ),
        reverse=True,
    )
    return candidates


def evaluate_candidates(
    candidates: list[dict[str, Any]],
    order: dict[str, Any],
) -> list[dict[str, Any]]:
    evaluated = []
    roster = list_service_technicians()
    for candidate in candidates:
        technician = next(
            item for item in roster if item["id"] == candidate["technician_id"]
        )
        status = "aprobado"
        alerts: list[str] = []
        potential_hours = technician["active_workload_hours"] + (
            candidate["calculated_travel_time_minutes"] + 90
        ) / 60
        if candidate.get("eligibility_status") == "rejected":
            status = "rechazado"
            alerts.extend(candidate.get("rejection_reasons", []))
        if potential_hours > 8 and not any("Exceso de jornada" in alert for alert in alerts):
            status = "rechazado"
            alerts.append(f"Exceso de jornada: {potential_hours:.1f}hs.")
        if candidate["gps_signal"] == "offline":
            alerts.append("Señal GPS offline; se utiliza la última zona.")
        evaluated.append(
            {**candidate, "validation_status": status, "alerts": alerts}
        )
    return evaluated


@router.post("/api/dispatch/simulate")
async def simulate_dispatch(request: Request) -> JSONResponse:
    body = await parse_body(request)
    if body is None:
        return JSONResponse({"error": "JSON inválido"}, status_code=400)
    order = next((item for item in orders if item["id"] == body.get("order_id")), None)
    if order is None:
        return JSONResponse({"error": "Orden no encontrada"}, status_code=404)
    environment = body.get(
        "environment",
        {"weather": "soleado", "traffic": "normal", "gps_signal": "online"},
    )
    candidates = build_candidates(order, environment)
    evaluated = evaluate_candidates(candidates, order)
    approved = [
        candidate
        for candidate in evaluated
        if candidate["validation_status"] == "aprobado"
    ]
    recommended = approved[0] if approved else None
    confidence = (
        build_confidence_evidence(recommended, evaluated)
        if recommended
        else None
    )
    response = {
        "order_id": order["id"],
        "recommended_assignment": (
            {
                "technician_id": recommended["technician_id"],
                "name": recommended["name"],
                "score": recommended["score"],
                "confidence": confidence,
                "travel_time": recommended["calculated_travel_time_minutes"],
                "reasoning": (
                    f"Se propone a {recommended['name']} "
                    f"(Score: {recommended['score']}). "
                    f"{recommended['memory_justification']}"
                ),
            }
            if recommended
            else None
        ),
        "candidates": evaluated,
        "agent_logs": {
            "capture": {"agent": "Capture Agent v2.1", "output": order},
            "analyze": {
                "agent": "Analyze Agent v2.1",
                "output": order["structured_data"],
            },
            "plan": {"agent": "Planning Agent v2.1", "output": candidates},
            "evaluate": {"agent": "Evaluation Agent v2.1", "output": evaluated},
            "learning": {
                "agent": "Learning Agent v2.1",
                "output": {"status": "Pendiente de confirmación del ticket."},
            },
        },
    }
    return JSONResponse(response)


@router.post("/api/dispatch/confirm")
async def confirm_dispatch(request: Request) -> JSONResponse:
    body = await parse_body(request)
    if body is None:
        return JSONResponse({"error": "JSON inválido"}, status_code=400)
    order = next((item for item in orders if item["id"] == body.get("order_id")), None)
    technician = get_service_technician(str(body.get("technician_id", "")))
    if order is None or technician is None:
        return JSONResponse({"error": "Orden o Técnico no encontrado"}, status_code=404)

    existing_visit = find_service_visit_by_order(str(order["id"]))
    if existing_visit is not None:
        return JSONResponse(
            {
                "message": "Asignación ya estaba registrada.",
                "learnings_updated": [],
                "visit": existing_visit,
            }
        )

    learnings = read_learnings()
    new_learnings: list[dict[str, Any]] = []
    duration = body.get("duration_minutes")
    visit_duration_minutes = 90
    if duration:
        try:
            minutes = int(duration)
            visit_duration_minutes = minutes
            deviation = minutes / 90
            if deviation < 0.85 or deviation > 1.15:
                key = (
                    f"tech_efficiency_{technician['id']}_"
                    f"{order['structured_data']['category'].lower()}"
                )
                item = {
                    "key": key,
                    "type": "calibracion_tiempo",
                    "learning_content": {
                        "description": (
                            f"{technician['name']} resolvió el servicio en "
                            f"{minutes} minutos."
                        ),
                        "parameters": {
                            "technician_id": technician["id"],
                            "skill": (
                                order["structured_data"]["required_skills"][0]
                                if order["structured_data"]["required_skills"]
                                else order["structured_data"]["category"]
                            ),
                            "modifier": round(deviation, 2),
                        },
                    },
                    "confidence": 0.80,
                    "updated_at": datetime.now(UTC).isoformat(),
                }
                learnings = [entry for entry in learnings if entry["key"] != key]
                learnings.append(item)
                new_learnings.append(item)
        except (TypeError, ValueError):
            pass

    feedback = str(body.get("feedback_comment", ""))
    if feedback.strip():
        key = f"preference_{order['zone'].lower()}_{technician['id']}"
        item = {
            "key": key,
            "type": "preferencia_usuario",
            "learning_content": {
                "description": (
                    f"Preferencia para {technician['name']} en {order['zone']}: "
                    f"'{feedback}'"
                ),
                "parameters": {
                    "technician_id": technician["id"],
                    "zone": order["zone"],
                    "comment": feedback,
                },
            },
            "confidence": 0.90,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        learnings = [entry for entry in learnings if entry["key"] != key]
        learnings.append(item)
        new_learnings.append(item)
    visit = create_service_visit(
        order=order,
        technician=technician,
        duration_minutes=visit_duration_minutes,
        feedback_comment=feedback,
    )
    order["status"] = "completada"
    update_service_technician(
        technician["id"],
        {"active_workload_hours": technician["active_workload_hours"] + 1.5},
    )
    write_learnings(learnings)
    return JSONResponse(
        {
            "message": "Asignación completada y feedback procesado.",
            "learnings_updated": new_learnings,
            "visit": visit,
        }
    )
