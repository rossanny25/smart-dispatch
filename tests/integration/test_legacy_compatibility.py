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
