import json
from pathlib import Path

from app.auth import DEFAULT_PASSWORD, DEFAULT_USERNAME
from app.main import create_app
from app.startup import prepare_runtime
from tests.asgi_client import request_asgi


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _app_with_runtime(tmp_path: Path):
    database_path = tmp_path / "runtime.db"
    prepare_runtime(database_path)
    return create_app(database_path=database_path)


def _admin_cookie(app: object) -> str:
    status, headers, _ = request_asgi(
        app,
        "/auth/login",
        method="POST",
        json_body={"username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD},
        authenticated=False,
    )
    assert status == 200
    return headers["set-cookie"].split(";", 1)[0]


def test_all_current_legacy_routes_remain_reachable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    learning_store = tmp_path / "learning_store.json"
    learning_store.write_bytes((PROJECT_ROOT / "data" / "learning_store.json").read_bytes())
    monkeypatch.setenv("SMART_DISPATCH_LEARNING_STORE_PATH", str(learning_store))

    app = _app_with_runtime(tmp_path)

    technicians_status, _, technicians_body = request_asgi(app, "/api/technicians")
    orders_status, _, orders_body = request_asgi(app, "/api/orders")
    memory_status, _, memory_body = request_asgi(app, "/api/memory/learning")
    create_status, _, create_body = request_asgi(
        app,
        "/api/orders",
        method="POST",
        json_body={
            "raw_text": "Corte de luz urgente",
            "address": "Av. Siempre Viva 123",
            "zone": "Belgrano",
        },
    )
    simulate_status, _, simulate_body = request_asgi(
        app,
        "/api/dispatch/simulate",
        method="POST",
        json_body={"order_id": "order_001"},
    )
    confirm_status, _, confirm_body = request_asgi(
        app,
        "/api/dispatch/confirm",
        method="POST",
        json_body={
            "order_id": "order_001",
            "technician_id": "tech_03",
            "duration_minutes": None,
            "feedback_comment": "",
        },
    )
    reset_status, _, reset_body = request_asgi(
        app,
        "/api/reset",
        method="POST",
        json_body={},
    )

    assert technicians_status == orders_status == memory_status == 200
    assert create_status == 201
    assert simulate_status == confirm_status == reset_status == 200
    assert len(json.loads(technicians_body)) == 5
    assert json.loads(orders_body)
    assert json.loads(memory_body)
    assert json.loads(create_body)["structured_data"]["category"] == "Electricidad"
    assert json.loads(simulate_body)["recommended_assignment"] is not None
    assert "learnings_updated" in json.loads(confirm_body)
    assert "message" in json.loads(reset_body)


def test_legacy_simulation_returns_hard_rule_evidence_for_all_technicians(
    tmp_path: Path,
    monkeypatch,
) -> None:
    learning_store = tmp_path / "learning_store.json"
    learning_store.write_bytes((PROJECT_ROOT / "data" / "learning_store.json").read_bytes())
    monkeypatch.setenv("SMART_DISPATCH_LEARNING_STORE_PATH", str(learning_store))

    from app.adapters.legacy import compatibility
    app = _app_with_runtime(tmp_path)

    compatibility.technicians[:] = compatibility.load_seed_list(
        compatibility.SEED_TECHNICIANS_PATH
    )
    compatibility.orders[:] = compatibility.load_seed_list(
        compatibility.SEED_ORDERS_PATH
    )

    status, _, body = request_asgi(
        app,
        "/api/dispatch/simulate",
        method="POST",
        json_body={"order_id": "order_001"},
    )

    payload = json.loads(body)
    candidates = payload["candidates"]
    rejected = [
        candidate
        for candidate in candidates
        if candidate["validation_status"] == "rechazado"
    ]

    assert status == 200
    assert len(candidates) == 5
    assert payload["recommended_assignment"]["technician_id"] == "tech_03"
    assert payload["recommended_assignment"]["confidence"]["label"] in {
        "alta",
        "media",
        "baja",
    }
    assert payload["recommended_assignment"]["confidence"]["value"] != (
        payload["recommended_assignment"]["score"] / 100
    )
    assert rejected
    assert all("hard_rule_checks" in candidate for candidate in candidates)
    assert all(len(candidate["hard_rule_checks"]) == 6 for candidate in candidates)
    assert all(candidate["score"] is None for candidate in rejected)
    assert any(
        any(check["key"] == "certifications" and check["status"] == "fail"
            for check in candidate["hard_rule_checks"])
        for candidate in rejected
    )


def test_legacy_simulation_does_not_force_recommendation_when_none_are_feasible(
    tmp_path: Path,
    monkeypatch,
) -> None:
    learning_store = tmp_path / "learning_store.json"
    learning_store.write_bytes((PROJECT_ROOT / "data" / "learning_store.json").read_bytes())
    monkeypatch.setenv("SMART_DISPATCH_LEARNING_STORE_PATH", str(learning_store))

    app = _app_with_runtime(tmp_path)
    cookie = _admin_cookie(app)
    _, _, technicians_body = request_asgi(app, "/api/technicians")
    for technician in json.loads(technicians_body):
        patch_status, _, _ = request_asgi(
            app,
            f"/api/technicians/{technician['id']}",
            method="PATCH",
            headers={
                "cookie": cookie,
                "idempotency-key": f"remove-skills-{technician['id']}",
            },
            json_body={"certifications": []},
            authenticated=False,
        )
        assert patch_status == 200
    status, _, body = request_asgi(
        app,
        "/api/dispatch/simulate",
        method="POST",
        json_body={"order_id": "order_001"},
    )

    payload = json.loads(body)
    assert status == 200
    assert payload["recommended_assignment"] is None
    assert len(payload["candidates"]) == 5
    assert all(
        candidate["validation_status"] == "rechazado"
        for candidate in payload["candidates"]
    )
    assert all(candidate["score"] is None for candidate in payload["candidates"])


def test_technicians_are_bootstrapped_from_sqlite_runtime(tmp_path: Path) -> None:
    app = _app_with_runtime(tmp_path)

    status, _, body = request_asgi(app, "/api/technicians")

    technicians = json.loads(body)
    assert status == 200
    assert len(technicians) == 5
    assert all("shift" in technician for technician in technicians)
    assert all("created_at" in technician for technician in technicians)


def test_admin_can_create_and_edit_service_technicians(tmp_path: Path) -> None:
    app = _app_with_runtime(tmp_path)
    cookie = _admin_cookie(app)

    create_status, _, create_body = request_asgi(
        app,
        "/api/technicians",
        method="POST",
        headers={"cookie": cookie, "idempotency-key": "create-marina"},
        json_body={
            "name": "Marina Ruiz",
            "status": "disponible",
            "zone": "Palermo",
            "certifications": ["Gasista Matriculado"],
            "shift": {"start": "10:00", "end": "18:00"},
            "active_workload_hours": 1.0,
            "rating": 4.4,
            "ppe": ["detector de gas"],
            "gps_coordinates": {"lat": -34.58, "lng": -58.42},
        },
        authenticated=False,
    )
    created = json.loads(create_body)["technician"]

    update_status, _, update_body = request_asgi(
        app,
        f"/api/technicians/{created['id']}",
        method="PATCH",
        headers={"cookie": cookie, "idempotency-key": "update-marina"},
        json_body={
            "certifications": ["Gasista Matriculado", "Técnico HVAC"],
            "shift": {"start": "09:00", "end": "17:00"},
            "active_workload_hours": 2.5,
        },
        authenticated=False,
    )

    assert create_status == 201
    assert created["name"] == "Marina Ruiz"
    assert update_status == 200
    updated = json.loads(update_body)["technician"]
    assert updated["shift"] == {"start": "09:00", "end": "17:00"}
    assert "Técnico HVAC" in updated["certifications"]


def test_non_admin_cannot_write_service_technicians(tmp_path: Path) -> None:
    app = _app_with_runtime(tmp_path)
    admin_cookie = _admin_cookie(app)
    request_asgi(
        app,
        "/api/v1/admin/users",
        method="POST",
        headers={"cookie": admin_cookie, "idempotency-key": "create-tech-user"},
        json_body={
            "username": "tecnico-ui",
            "display_name": "Tecnico UI",
            "role": "tecnico",
            "password": "tecnico2026",
        },
        authenticated=False,
    )
    status, headers, _ = request_asgi(
        app,
        "/auth/login",
        method="POST",
        json_body={"username": "tecnico-ui", "password": "tecnico2026"},
        authenticated=False,
    )
    assert status == 200
    technician_cookie = headers["set-cookie"].split(";", 1)[0]

    status, _, body = request_asgi(
        app,
        "/api/technicians",
        method="POST",
        headers={"cookie": technician_cookie, "idempotency-key": "blocked-tech-write"},
        json_body={
            "name": "Sin Permiso",
            "status": "disponible",
            "zone": "Centro",
            "certifications": [],
            "shift": {"start": "09:00", "end": "17:00"},
            "active_workload_hours": 0,
            "rating": 4,
        },
        authenticated=False,
    )

    assert status == 403
    assert json.loads(body) == {"error": "admin_required"}

    reset_status, _, reset_body = request_asgi(
        app,
        "/api/reset",
        method="POST",
        headers={"cookie": technician_cookie},
        json_body={},
        authenticated=False,
    )

    assert reset_status == 403
    assert json.loads(reset_body) == {"error": "admin_required"}


def test_edited_technician_roster_changes_dispatch_eligibility(tmp_path: Path) -> None:
    app = _app_with_runtime(tmp_path)
    cookie = _admin_cookie(app)

    status, _, body = request_asgi(app, "/api/technicians")
    tech_03 = next(item for item in json.loads(body) if item["id"] == "tech_03")
    assert status == 200

    patch_status, _, patch_body = request_asgi(
        app,
        "/api/technicians/tech_03",
        method="PATCH",
        headers={"cookie": cookie, "idempotency-key": "remove-tech-03-skills"},
        json_body={"certifications": []},
        authenticated=False,
    )
    assert patch_status == 200, patch_body
    simulate_status, _, simulate_body = request_asgi(
        app,
        "/api/dispatch/simulate",
        method="POST",
        json_body={"order_id": "order_001"},
    )

    candidate = next(
        item for item in json.loads(simulate_body)["candidates"] if item["technician_id"] == "tech_03"
    )
    assert simulate_status == 200
    assert candidate["validation_status"] == "rechazado"
    assert any(check["key"] == "certifications" for check in candidate["hard_rule_checks"])


def test_unclear_order_text_is_rejected_before_insertion(tmp_path: Path) -> None:
    app = _app_with_runtime(tmp_path)

    before_status, _, before_body = request_asgi(app, "/api/orders")
    status, _, body = request_asgi(
        app,
        "/api/orders",
        method="POST",
        json_body={
            "raw_text": "asdfasdf",
            "address": "sdfasfasfsa",
            "zone": "Palermo",
        },
    )
    after_status, _, after_body = request_asgi(app, "/api/orders")

    assert before_status == after_status == 200
    assert status == 422
    assert json.loads(body)["error"] == "Solicitud no entendida"
    assert json.loads(before_body) == json.loads(after_body)


def test_technician_create_requires_and_replays_idempotency_key(tmp_path: Path) -> None:
    app = _app_with_runtime(tmp_path)
    cookie = _admin_cookie(app)
    payload = {
        "name": "Tecnico Idempotente",
        "status": "disponible",
        "zone": "Centro",
        "certifications": ["Redes WAN"],
        "shift": {"start": "09:00", "end": "17:00"},
        "active_workload_hours": 1,
        "rating": 4,
        "gps_coordinates": {"lat": -34.6, "lng": -58.38},
    }

    missing_status, _, missing_body = request_asgi(
        app,
        "/api/technicians",
        method="POST",
        headers={"cookie": cookie},
        json_body=payload,
        authenticated=False,
    )
    first_status, _, first_body = request_asgi(
        app,
        "/api/technicians",
        method="POST",
        headers={"cookie": cookie, "idempotency-key": "create-idempotent-tech"},
        json_body=payload,
        authenticated=False,
    )
    second_status, _, second_body = request_asgi(
        app,
        "/api/technicians",
        method="POST",
        headers={"cookie": cookie, "idempotency-key": "create-idempotent-tech"},
        json_body=payload,
        authenticated=False,
    )
    conflict_payload = {**payload, "name": "Tecnico Idempotente Alterado"}
    conflict_status, _, conflict_body = request_asgi(
        app,
        "/api/technicians",
        method="POST",
        headers={"cookie": cookie, "idempotency-key": "create-idempotent-tech"},
        json_body=conflict_payload,
        authenticated=False,
    )

    assert missing_status == 422
    assert json.loads(missing_body)["error"] == "idempotency_key_required"
    assert first_status == second_status == 201
    assert json.loads(second_body) == json.loads(first_body)
    assert conflict_status == 409
    assert json.loads(conflict_body)["error"] == "idempotency_conflict"


def test_technician_payload_rejects_non_finite_and_unknown_fields(tmp_path: Path) -> None:
    app = _app_with_runtime(tmp_path)
    cookie = _admin_cookie(app)

    status, _, body = request_asgi(
        app,
        "/api/technicians",
        method="POST",
        headers={"cookie": cookie, "idempotency-key": "invalid-tech"},
        json_body={
            "name": "Tecnico Invalido",
            "status": "disponible",
            "zone": "Centro",
            "certifications": [123],
            "shift": {"start": "09:00", "end": "17:00"},
            "active_workload_hours": "NaN",
            "rating": 4,
            "unknown": True,
        },
        authenticated=False,
    )

    assert status == 422
    assert json.loads(body)["error"] == "technician_invalid"


def test_terse_known_order_text_is_accepted_with_numbered_address(tmp_path: Path) -> None:
    app = _app_with_runtime(tmp_path)

    status, _, body = request_asgi(
        app,
        "/api/orders",
        method="POST",
        json_body={
            "raw_text": "fuga gas",
            "address": "Sucursal Palermo 123",
            "zone": "Palermo",
        },
    )

    assert status == 201
    assert json.loads(body)["structured_data"]["category"] == "Gas"


def test_hard_rules_fail_closed_for_required_ppe_and_invalid_shift() -> None:
    from app.adapters.legacy.compatibility import build_hard_rule_checks

    order = {
        "structured_data": {
            "required_skills": ["Técnico Electricista A"],
            "required_ppe": ["arnés dieléctrico"],
        }
    }
    technician = {
        "status": "disponible",
        "certifications": ["Técnico Electricista A"],
        "shift": {"start": "bad", "end": "16:00"},
        "active_workload_hours": 1,
        "ppe": [],
    }

    checks, rejection_reasons, _ = build_hard_rule_checks(
        technician,
        order,
        travel_minutes=30,
    )

    by_key = {check["key"]: check for check in checks}
    assert by_key["shift"]["status"] == "fail"
    assert by_key["ppe"]["status"] == "fail"
    assert "Turno ausente o inválido" in rejection_reasons
    assert "Falta EPP: arnés dieléctrico" in rejection_reasons


def test_hard_rules_accept_valid_overnight_shift() -> None:
    from app.adapters.legacy.compatibility import build_hard_rule_checks

    order = {"structured_data": {"required_skills": [], "required_ppe": []}}
    technician = {
        "status": "disponible",
        "certifications": [],
        "shift": {"start": "22:00", "end": "06:00"},
        "active_workload_hours": 1,
    }

    checks, rejection_reasons, _ = build_hard_rule_checks(
        technician,
        order,
        travel_minutes=30,
    )

    by_key = {check["key"]: check for check in checks}
    assert by_key["shift"]["status"] == "pass"
    assert not rejection_reasons


def test_canonical_and_server_entrypoints_use_same_app_and_keep_legacy_routes() -> None:
    import server
    from app.main import app
    from app.runtime import main

    assert server.main is main
    status, _, body = request_asgi(app, "/api/technicians")
    assert status == 200
    assert json.loads(body)


def test_server_file_is_only_a_compatibility_launcher() -> None:
    source = (PROJECT_ROOT / "server.py").read_text(encoding="utf-8")

    assert "from app.runtime import main" in source
    assert "SmartDispatchHTTPHandler" not in source
    assert "technicians =" not in source


def test_default_confirmation_writes_runtime_copy_and_preserves_seed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from app.adapters.legacy import compatibility

    seed_path = tmp_path / "learning_store.json"
    runtime_path = tmp_path / "learning_store.runtime.json"
    seed_bytes = (PROJECT_ROOT / "data" / "learning_store.json").read_bytes()
    seed_path.write_bytes(seed_bytes)
    monkeypatch.delenv("SMART_DISPATCH_LEARNING_STORE_PATH", raising=False)
    monkeypatch.setattr(compatibility, "SEED_LEARNING_STORE_PATH", seed_path)
    monkeypatch.setattr(compatibility, "DEFAULT_LEARNING_STORE_PATH", runtime_path)
    app = _app_with_runtime(tmp_path)

    status, _, body = request_asgi(
        app,
        "/api/dispatch/confirm",
        method="POST",
        json_body={
            "order_id": "order_001",
            "technician_id": "tech_03",
            "duration_minutes": 120,
            "feedback_comment": "Preferido para la demostración",
        },
    )

    assert status == 200
    assert json.loads(body)["learnings_updated"]
    assert seed_path.read_bytes() == seed_bytes
    assert runtime_path.exists()
    assert runtime_path.read_bytes() != seed_bytes


def test_reset_reloads_runtime_learning_store_from_seed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from app.adapters.legacy import compatibility
    from app.main import app

    seed_path = tmp_path / "learning_store.json"
    runtime_path = tmp_path / "learning_store.runtime.json"
    seed_bytes = (PROJECT_ROOT / "data" / "learning_store.json").read_bytes()
    seed_path.write_bytes(seed_bytes)
    runtime_path.write_text(
        json.dumps(
            [
                {
                    "key": "dirty",
                    "type": "preferencia_usuario",
                    "learning_content": {"description": "dirty", "parameters": {}},
                    "confidence": 1,
                    "updated_at": "2026-08-11T00:00:00+00:00",
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(compatibility, "SEED_LEARNING_STORE_PATH", seed_path)
    monkeypatch.setattr(compatibility, "DEFAULT_LEARNING_STORE_PATH", runtime_path)
    monkeypatch.delenv("SMART_DISPATCH_LEARNING_STORE_PATH", raising=False)

    status, _, _ = request_asgi(
        app,
        "/api/reset",
        method="POST",
        json_body={},
    )

    assert status == 200
    assert json.loads(runtime_path.read_text(encoding="utf-8")) == json.loads(
        seed_bytes.decode("utf-8")
    )
