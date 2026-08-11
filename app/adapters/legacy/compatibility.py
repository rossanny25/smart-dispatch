"""Mechanical FastAPI relocation of the original ``server.py`` API behavior."""

from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.adapters.persistence.database import PROJECT_ROOT


router = APIRouter(include_in_schema=False)
LEARNING_STORE_PATH_ENV = "SMART_DISPATCH_LEARNING_STORE_PATH"
SEED_DATA_DIR = PROJECT_ROOT / "data" / "seeds"
SEED_TECHNICIANS_PATH = SEED_DATA_DIR / "technicians.json"
SEED_ORDERS_PATH = SEED_DATA_DIR / "orders.json"
SEED_LEARNING_STORE_PATH = PROJECT_ROOT / "data" / "learning_store.json"
DEFAULT_LEARNING_STORE_PATH = PROJECT_ROOT / "data" / "learning_store.runtime.json"


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


def get_distance(zone_a: str, zone_b: str) -> float:
    return ZONE_DISTANCES.get(zone_a, {}).get(zone_b, 8.0)


async def parse_body(request: Request) -> dict[str, Any] | None:
    try:
        value = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return value if isinstance(value, dict) else None


@router.get("/api/technicians")
async def list_technicians() -> list[dict[str, Any]]:
    return technicians


@router.get("/api/orders")
async def list_orders() -> list[dict[str, Any]]:
    return orders


@router.get("/api/memory/learning")
async def list_memory() -> list[dict[str, Any]]:
    return read_learnings()


@router.post("/api/reset")
async def reset_simulation() -> dict[str, str]:
    init_storage()
    technicians[:] = load_seed_list(SEED_TECHNICIANS_PATH)
    orders[:] = load_seed_list(SEED_ORDERS_PATH)
    return {"message": "Estado de simulación y memoria restablecidos."}


def classify_order(raw_text: str) -> tuple[str, int, list[str]]:
    text = raw_text.lower()
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
    for technician in technicians:
        if required and not all(
            skill in technician["certifications"] for skill in required
        ):
            continue
        distance_km = get_distance(technician["zone"], order["zone"])
        travel_minutes = distance_km * 4
        if environment.get("traffic") == "congestionado":
            travel_minutes += distance_km * 5
        if environment.get("weather") == "lluvia_extrema":
            travel_minutes += 15

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
        score = min(100, max(0, int(50 + proximity + workload + memory_bonus - gps_penalty)))
        candidates.append(
            {
                "technician_id": technician["id"],
                "name": technician["name"],
                "zone": technician["zone"],
                "score": score,
                "calculated_travel_time_minutes": int(travel_minutes),
                "distance_km": distance_km,
                "active_workload_hours": technician["active_workload_hours"],
                "memory_bonus": memory_bonus,
                "memory_justification": (
                    " ".join(memory_notes)
                    if memory_notes
                    else "Sin datos históricos específicos."
                ),
                "gps_signal": environment.get("gps_signal"),
            }
        )
    candidates.sort(key=lambda candidate: candidate["score"], reverse=True)
    return candidates


def evaluate_candidates(
    candidates: list[dict[str, Any]],
    order: dict[str, Any],
) -> list[dict[str, Any]]:
    evaluated = []
    for candidate in candidates:
        technician = next(
            item for item in technicians if item["id"] == candidate["technician_id"]
        )
        status = "aprobado"
        alerts: list[str] = []
        potential_hours = technician["active_workload_hours"] + (
            candidate["calculated_travel_time_minutes"] + 90
        ) / 60
        if potential_hours > 8:
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
    response = {
        "order_id": order["id"],
        "recommended_assignment": (
            {
                "technician_id": recommended["technician_id"],
                "name": recommended["name"],
                "score": recommended["score"],
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
    technician = next(
        (item for item in technicians if item["id"] == body.get("technician_id")),
        None,
    )
    if order is None or technician is None:
        return JSONResponse({"error": "Orden o Técnico no encontrado"}, status_code=404)

    order["status"] = "completada"
    technician["active_workload_hours"] += 1.5
    learnings = read_learnings()
    new_learnings: list[dict[str, Any]] = []
    duration = body.get("duration_minutes")
    if duration:
        try:
            minutes = int(duration)
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
    write_learnings(learnings)
    return JSONResponse(
        {
            "message": "Asignación completada y feedback procesado.",
            "learnings_updated": new_learnings,
        }
    )
