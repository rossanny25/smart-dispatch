import json
import inspect
from datetime import UTC, datetime, timedelta
from pathlib import Path
import uuid

import pytest
from sqlalchemy import text

from app.adapters.persistence.database import create_sqlite_engine
from app.main import create_app
from app.migrations.runtime import upgrade_to_head
from tests.asgi_client import request_asgi


@pytest.fixture
def dispatch_app(tmp_path: Path):
    database_path = tmp_path / "dispatch.db"
    upgrade_to_head(database_path)
    return create_app(database_path=database_path), database_path


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _create_work_order(app) -> str:
    status, _, raw = request_asgi(
        app,
        "/api/v1/work-orders",
        method="POST",
        json_body={
            "incident_text": "Fuga de gas urgente",
            "address": "Av. Curso 123",
            "zone": "Centro",
            "context": None,
        },
        headers={
            "content-type": "application/json",
            "idempotency-key": "work-order-for-dispatch",
        },
    )
    assert status == 201
    return json.loads(raw)["data"]["id"]


def _dispatch_body(work_order_id: str, *, available: bool = True) -> dict:
    captured = datetime.now(UTC).replace(microsecond=0)
    technician_id = "33333333-3333-4333-8333-333333333333"
    return {
        "schema_version": "v1",
        "work_order_id": work_order_id,
        "captured_at": _iso(captured),
        "technicians": [
            {
                "technician_id": technician_id,
                "availability": "available" if available else "busy",
                "certifications": ["gas_registered"],
                "shift_start": _iso(captured - timedelta(hours=4)),
                "shift_end": _iso(captured + timedelta(hours=4)),
                "assigned_work_minutes": 120,
                "accumulated_driving_minutes": 30,
                "has_required_epp": True,
                "estimated_travel_minutes": 20,
                "distance_meters": 10_000,
            }
        ],
        "technician_quality": [
            {
                "technician_id": technician_id,
                "quality_rating_0_to_5": "4.5",
            }
        ],
        "gps_observations": [
            {
                "technician_id": technician_id,
                "observed_at": _iso(captured - timedelta(minutes=5)),
                "last_known_zone": "Centro",
            }
        ],
        "traffic_observed_at": _iso(captured - timedelta(minutes=2)),
        "weather_observed_at": _iso(captured - timedelta(minutes=3)),
        "active_supporting_episode_count": 0,
        "memory_experiment_mode": "disabled",
    }


def _post_run(app, body, key="dispatch-run-1"):
    return request_asgi(
        app,
        "/api/v1/dispatch-runs",
        method="POST",
        json_body=body,
        headers={
            "content-type": "application/json",
            "idempotency-key": key,
        },
    )


def test_dispatch_run_executes_persists_replays_and_can_be_queried(
    dispatch_app,
) -> None:
    app, database_path = dispatch_app
    work_order_id = _create_work_order(app)
    request = _dispatch_body(work_order_id)

    status, headers, raw = _post_run(app, request)
    assert status == 201
    assert headers["idempotent-replay"] == "false"
    payload = json.loads(raw)
    resource = payload["data"]
    run_id = resource["run_id"]
    uuid.UUID(run_id)
    assert resource["state"] == "WAIT_FOR_DECISION"
    assert [item["stage"] for item in resource["stage_executions"]] == [
        "CAPTURE",
        "ANALYZE",
        "PLAN",
        "EVALUATE",
    ]
    assert resource["recommendation"]["technician_id"].startswith("33333333")
    assert len(resource["recommendation"]["scoring"]["components"]) == 5
    assert resource["recommendation"]["scoring"]["components"][0]["name"] == "sla"
    assert len(resource["recommendation"]["factors"]) == 4
    assert resource["recommendation"]["explanation"]["template_id"] == (
        "CONFIDENCE_SUMMARY"
    )
    assert resource["candidate_evaluations"][0]["eligible"] is True
    assert resource["candidate_evaluations"][0]["scoring"]["rank"] == 1

    replay_status, replay_headers, replay_raw = _post_run(app, request)
    assert replay_status == 201
    assert replay_headers["idempotent-replay"] == "true"
    assert json.loads(replay_raw)["data"] == resource

    get_status, _, get_raw = request_asgi(
        app, f"/api/v1/dispatch-runs/{run_id}"
    )
    assert get_status == 200
    assert json.loads(get_raw)["data"] == resource

    engine = create_sqlite_engine(database_path)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM dispatch_runs")).scalar_one() == 1
            assert connection.execute(text("SELECT count(*) FROM stage_executions")).scalar_one() == 4
            assert connection.execute(text("SELECT count(*) FROM state_transitions")).scalar_one() == 5
            assert connection.execute(text("SELECT count(*) FROM work_order_analyses")).scalar_one() == 0
            assert connection.execute(text("SELECT count(*) FROM eligibility_evaluation_sets")).scalar_one() == 0
            assert connection.execute(text("SELECT count(*) FROM scoring_evaluation_sets")).scalar_one() == 0
            assert connection.execute(text("SELECT count(*) FROM confidence_evaluation_sets")).scalar_one() == 0
    finally:
        engine.dispose()


def test_no_feasible_candidates_is_a_success_with_full_rejection_evidence(
    dispatch_app,
) -> None:
    app, _ = dispatch_app
    work_order_id = _create_work_order(app)

    status, _, raw = _post_run(
        app,
        _dispatch_body(work_order_id, available=False),
        key="no-feasible",
    )

    assert status == 201
    resource = json.loads(raw)["data"]
    assert resource["state"] == "NO_FEASIBLE_CANDIDATES"
    assert resource["recommendation"] is None
    candidate = resource["candidate_evaluations"][0]
    assert candidate["eligible"] is False
    assert candidate["objective_score"] is None
    assert candidate["rank"] is None
    assert any(
        check["reason"] == "TECHNICIAN_UNAVAILABLE"
        for check in candidate["eligibility"]["checks"]
    )


def test_stage_failure_retains_prior_evidence_without_partial_output(
    dispatch_app,
) -> None:
    app, _ = dispatch_app
    work_order_id = _create_work_order(app)
    included_v1 = app.routes[4].original_router
    dispatch_router = included_v1.routes[1].original_router
    endpoint = dispatch_router.routes[0].endpoint
    orchestrator = inspect.getclosurevars(endpoint).nonlocals["orchestrator"]

    class CrashingAnalyze:
        def execute(self, request):
            raise RuntimeError("private adapter failure")

    orchestrator._stage = CrashingAnalyze()
    failed_request = _dispatch_body(work_order_id)
    status, _, raw = _post_run(app, failed_request, key="failed-stage")

    assert status == 500
    error = json.loads(raw)["error"]
    assert error["code"] == "DISPATCH_RUN_FAILED"
    run_id = error["details"][0]["message"]
    get_status, _, get_raw = request_asgi(
        app, f"/api/v1/dispatch-runs/{run_id}"
    )
    assert get_status == 200
    resource = json.loads(get_raw)["data"]
    assert resource["state"] == "FAILED"
    assert resource["failure"] == {
        "stage": "ANALYZE",
        "code": "ANALYZE_FAILED",
        "type": "STAGE_FAILURE",
    }
    assert [item["status"] for item in resource["stage_executions"]] == [
        "completed",
        "failed",
    ]
    assert resource["stage_executions"][-1]["output_ref"] is None
    assert "capture" in resource["artifacts"]
    assert resource["artifacts"]["analyze"] is None

    replay_status, _, replay_raw = _post_run(
        app,
        failed_request,
        key="failed-stage",
    )
    assert replay_status == 500
    assert json.loads(replay_raw)["error"]["details"][0]["message"] == run_id


def test_get_rejects_corrupted_child_evidence(dispatch_app) -> None:
    app, database_path = dispatch_app
    work_order_id = _create_work_order(app)
    status, _, raw = _post_run(
        app, _dispatch_body(work_order_id), key="corruption-check"
    )
    assert status == 201
    run_id = json.loads(raw)["data"]["run_id"]
    engine = create_sqlite_engine(database_path)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE stage_executions SET duration_ms = duration_ms + 1 "
                    "WHERE run_id = :run_id AND sequence = 1"
                ),
                {"run_id": run_id},
            )
    finally:
        engine.dispose()

    get_status, _, get_raw = request_asgi(
        app, f"/api/v1/dispatch-runs/{run_id}"
    )
    assert get_status == 500
    assert json.loads(get_raw)["error"]["code"] == "PERSISTENCE_ERROR"


def test_dispatch_idempotency_conflict_does_not_create_another_run(
    dispatch_app,
) -> None:
    app, database_path = dispatch_app
    work_order_id = _create_work_order(app)
    first = _dispatch_body(work_order_id)
    assert _post_run(app, first, key="same-key")[0] == 201
    changed = json.loads(json.dumps(first))
    changed["active_supporting_episode_count"] = 2
    status, _, raw = _post_run(app, changed, key="same-key")
    assert status == 409
    assert json.loads(raw)["error"]["code"] == "CONFLICT"
    engine = create_sqlite_engine(database_path)
    try:
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT count(*) FROM dispatch_runs")
            ).scalar_one() == 1
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("method_name", "expected_stage", "completed_before_failure"),
    [
        ("_plan_from_snapshot", "PLAN", 2),
        ("_evaluate_from_plan", "EVALUATE", 3),
    ],
)
def test_later_stage_failures_preserve_every_prior_commit(
    dispatch_app,
    method_name,
    expected_stage,
    completed_before_failure,
) -> None:
    app, database_path = dispatch_app
    work_order_id = _create_work_order(app)
    endpoint = (
        app.routes[4]
        .original_router.routes[1]
        .original_router.routes[0]
        .endpoint
    )
    orchestrator = inspect.getclosurevars(endpoint).nonlocals["orchestrator"]

    def crash(*args, **kwargs):
        raise RuntimeError("private failure")

    setattr(orchestrator, method_name, crash)
    status, _, raw = _post_run(
        app,
        _dispatch_body(work_order_id),
        key=f"failure-{expected_stage.lower()}",
    )
    assert status == 500
    run_id = json.loads(raw)["error"]["details"][0]["message"]
    get_status, _, get_raw = request_asgi(
        app, f"/api/v1/dispatch-runs/{run_id}"
    )
    assert get_status == 200
    resource = json.loads(get_raw)["data"]
    assert resource["state"] == "FAILED"
    assert resource["failure"]["stage"] == expected_stage
    assert sum(
        item["status"] == "completed"
        for item in resource["stage_executions"]
    ) == completed_before_failure
    assert resource["stage_executions"][-1]["status"] == "failed"
    engine = create_sqlite_engine(database_path)
    try:
        with engine.connect() as connection:
            assert connection.execute(
                text(
                    "SELECT count(*) FROM run_snapshots "
                    "WHERE run_id = :run_id"
                ),
                {"run_id": run_id},
            ).scalar_one() == completed_before_failure + 1
    finally:
        engine.dispose()


def test_dispatch_transport_and_openapi_contracts_are_declared(
    dispatch_app,
) -> None:
    app, _ = dispatch_app
    status, _, raw = request_asgi(
        app,
        "/api/v1/dispatch-runs",
        method="POST",
        body=b"{}",
        headers={"content-type": "text/plain", "idempotency-key": "bad-media"},
    )
    assert status == 415
    assert json.loads(raw)["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"

    status, _, raw = _post_run(app, {"unexpected": True}, key="invalid")
    assert status == 422
    assert json.loads(raw)["error"]["code"] == "VALIDATION_FAILED"

    responses = app.openapi()["paths"]["/api/v1/dispatch-runs"]["post"][
        "responses"
    ]
    assert {"201", "409", "413", "415", "422", "500"}.issubset(responses)
