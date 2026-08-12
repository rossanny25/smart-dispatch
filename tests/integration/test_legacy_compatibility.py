import json
from pathlib import Path

from tests.asgi_client import request_asgi


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_all_current_legacy_routes_remain_reachable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    learning_store = tmp_path / "learning_store.json"
    learning_store.write_bytes((PROJECT_ROOT / "data" / "learning_store.json").read_bytes())
    monkeypatch.setenv("SMART_DISPATCH_LEARNING_STORE_PATH", str(learning_store))

    from app.main import app

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
    from app.main import app

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

    from app.adapters.legacy import compatibility
    from app.main import app

    original_technicians = [item.copy() for item in compatibility.technicians]
    try:
        for technician in compatibility.technicians:
            technician["certifications"] = []
        status, _, body = request_asgi(
            app,
            "/api/dispatch/simulate",
            method="POST",
            json_body={"order_id": "order_001"},
        )
    finally:
        compatibility.technicians[:] = original_technicians

    payload = json.loads(body)
    assert status == 200
    assert payload["recommended_assignment"] is None
    assert len(payload["candidates"]) == 5
    assert all(
        candidate["validation_status"] == "rechazado"
        for candidate in payload["candidates"]
    )
    assert all(candidate["score"] is None for candidate in payload["candidates"])


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
    from app.main import app

    seed_path = tmp_path / "learning_store.json"
    runtime_path = tmp_path / "learning_store.runtime.json"
    seed_bytes = (PROJECT_ROOT / "data" / "learning_store.json").read_bytes()
    seed_path.write_bytes(seed_bytes)
    monkeypatch.delenv("SMART_DISPATCH_LEARNING_STORE_PATH", raising=False)
    monkeypatch.setattr(compatibility, "SEED_LEARNING_STORE_PATH", seed_path)
    monkeypatch.setattr(compatibility, "DEFAULT_LEARNING_STORE_PATH", runtime_path)

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
