from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.adapters.persistence.unit_of_work import SqliteUnitOfWorkFactory
from app.adapters.stages.deterministic_analyze import DeterministicAnalyzeStage
from app.application.commands.analyze_work_order import (
    AnalyzeWorkOrder,
    AnalyzeWorkOrderRequest,
)
from app.application.commands.determine_technician_eligibility import (
    DetermineTechnicianEligibility,
    DetermineTechnicianEligibilityRequest,
)
from app.application.commands.score_eligible_technicians import (
    InvalidScoringInput,
    ScoreEligibleTechnicians,
    ScoreEligibleTechniciansRequest,
    ScoringPersistenceError,
    ScoringPolicyFailure,
)
from app.domain.work_orders.models import WorkOrder
from app.migrations.runtime import upgrade_to_head


TECH_1 = "33333333-3333-4333-8333-333333333333"
TECH_2 = "44444444-4444-4444-8444-444444444444"


def _prepare_eligibility(
    factory: SqliteUnitOfWorkFactory,
    *,
    first_availability: str = "available",
    first_travel_minutes: int = 30,
    sla_minutes: int = 60,
) -> str:
    context = (
        None
        if sla_minutes == 60
        else {
            "dispatch_requirements": {
                "category": "gas",
                "priority": 5,
                "sla_target_minutes": sla_minutes,
                "required_certifications": ["gas_registered"],
                "estimated_service_duration_minutes": 90,
            }
        }
    )
    work_order = WorkOrder(
        id=UUID("11111111-1111-4111-8111-111111111111"),
        schema_version="v1",
        raw_input={
            "incident_text": "Fuga de gas",
            "address": "Calle privada",
            "zone": "Centro",
            "context": context,
        },
        incident_text="Fuga de gas",
        address="Calle privada",
        zone="Centro",
        context=context,
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )
    with factory() as uow:
        uow.work_orders.add(work_order)
    analysis_id = AnalyzeWorkOrder(
        unit_of_work_factory=factory,
        stage=DeterministicAnalyzeStage(),
        uuid_factory=lambda: UUID("22222222-2222-4222-8222-222222222222"),
        clock=lambda: datetime(2026, 7, 28, 12, tzinfo=UTC),
    ).execute(
        AnalyzeWorkOrderRequest(work_order_id=str(work_order.id))
    ).analysis_id
    technicians = (
        {
            "technician_id": TECH_1,
            "availability": first_availability,
            "certifications": ["gas_registered"],
            "shift_start": "2026-07-28T08:00:00Z",
            "shift_end": "2026-07-28T18:00:00Z",
            "assigned_work_minutes": 300,
            "accumulated_driving_minutes": 100,
            "has_required_epp": True,
            "estimated_travel_minutes": first_travel_minutes,
            "distance_meters": 60_000,
        },
        {
            "technician_id": TECH_2,
            "availability": "busy",
            "certifications": ["gas_registered"],
            "shift_start": "2026-07-28T08:00:00Z",
            "shift_end": "2026-07-28T18:00:00Z",
            "assigned_work_minutes": 100,
            "accumulated_driving_minutes": 20,
            "has_required_epp": True,
            "estimated_travel_minutes": 20,
            "distance_meters": 10_000,
        },
    )
    return DetermineTechnicianEligibility(
        unit_of_work_factory=factory,
        uuid_factory=lambda: UUID("55555555-5555-4555-8555-555555555555"),
        clock=lambda: datetime(2026, 7, 28, 12, 1, tzinfo=UTC),
    ).execute(
        DetermineTechnicianEligibilityRequest(
            analysis_id=analysis_id,
            captured_at=datetime(2026, 7, 28, 12, tzinfo=UTC),
            technicians=technicians,
        )
    ).evaluation_set_id


def _request(evaluation_id: str, quality: str | None = "4") -> ScoreEligibleTechniciansRequest:
    return ScoreEligibleTechniciansRequest(
        eligibility_evaluation_set_id=evaluation_id,
        technician_quality=(
            {
                "technician_id": TECH_1,
                "quality_rating_0_to_5": quality,
            },
            {
                "technician_id": TECH_2,
                "quality_rating_0_to_5": None,
            },
        ),
    )


def test_real_sqlite_scoring_round_trip_replay_and_changed_quality(
    tmp_path: Path,
) -> None:
    path = tmp_path / "scoring.db"
    upgrade_to_head(path)
    factory = SqliteUnitOfWorkFactory(path)
    eligibility_id = _prepare_eligibility(factory)
    ids = iter(
        (
            UUID("66666666-6666-4666-8666-666666666666"),
            UUID("77777777-7777-4777-8777-777777777777"),
        )
    )
    command = ScoreEligibleTechnicians(
        unit_of_work_factory=factory,
        uuid_factory=lambda: next(ids),
        clock=lambda: datetime(2026, 7, 28, 12, 2, tzinfo=UTC),
    )

    first = command.execute(_request(eligibility_id))
    replay = command.execute(_request(eligibility_id))
    changed = command.execute(_request(eligibility_id, "4.5"))

    assert first.replayed is False
    assert replay.replayed is True
    assert replay.evaluation_set_id == first.evaluation_set_id
    assert changed.evaluation_set_id != first.evaluation_set_id
    assert [item["technician_id"] for item in first.output["eligible_candidates"]] == [
        TECH_1
    ]
    assert first.output["ineligible_candidates"][0]["eligibility"]["checks"][0][
        "reason"
    ] == "TECHNICIAN_UNAVAILABLE"
    with factory._get_engine().connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM scoring_evaluation_sets")
        ).scalar_one() == 2
    factory.dispose()


def test_scoring_rejects_incomplete_roster_and_corrupt_replay(
    tmp_path: Path,
) -> None:
    path = tmp_path / "corrupt-scoring.db"
    upgrade_to_head(path)
    factory = SqliteUnitOfWorkFactory(path)
    eligibility_id = _prepare_eligibility(factory)
    command = ScoreEligibleTechnicians(
        unit_of_work_factory=factory,
        uuid_factory=lambda: UUID("66666666-6666-4666-8666-666666666666"),
        clock=lambda: datetime(2026, 7, 28, 12, 2, tzinfo=UTC),
    )
    with pytest.raises(InvalidScoringInput):
        command.execute(
            ScoreEligibleTechniciansRequest(
                eligibility_evaluation_set_id=eligibility_id,
                technician_quality=(_request(eligibility_id).technician_quality[0],),
            )
        )
    first = command.execute(_request(eligibility_id))
    with factory._get_engine().begin() as connection:
        connection.execute(
            text(
                "UPDATE scoring_evaluation_sets "
                "SET top_objective_score = '99' WHERE id = :id"
            ),
            {"id": first.evaluation_set_id},
        )
    with pytest.raises(ScoringPersistenceError):
        command.execute(_request(eligibility_id))
    factory.dispose()


def test_fractional_scoring_and_no_feasible_sets_persist_canonically(
    tmp_path: Path,
) -> None:
    fractional_path = tmp_path / "fractional.db"
    upgrade_to_head(fractional_path)
    fractional_factory = SqliteUnitOfWorkFactory(fractional_path)
    fractional_id = _prepare_eligibility(
        fractional_factory,
        first_travel_minutes=1,
        sla_minutes=3,
    )
    fractional = ScoreEligibleTechnicians(
        unit_of_work_factory=fractional_factory,
        uuid_factory=lambda: UUID(
            "66666666-6666-4666-8666-666666666666"
        ),
        clock=lambda: datetime(2026, 7, 28, 12, 2, tzinfo=UTC),
    ).execute(_request(fractional_id))
    assert fractional.output["eligible_candidates"][0]["components"][0][
        "normalized_value"
    ] == "66.66666666666666666666666666666667"
    fractional_factory.dispose()

    empty_path = tmp_path / "no-feasible.db"
    upgrade_to_head(empty_path)
    empty_factory = SqliteUnitOfWorkFactory(empty_path)
    empty_id = _prepare_eligibility(
        empty_factory,
        first_availability="busy",
    )
    empty = ScoreEligibleTechnicians(
        unit_of_work_factory=empty_factory,
        uuid_factory=lambda: UUID(
            "66666666-6666-4666-8666-666666666666"
        ),
        clock=lambda: datetime(2026, 7, 28, 12, 2, tzinfo=UTC),
    ).execute(_request(empty_id))
    assert empty.output["eligible_candidates"] == []
    assert len(empty.output["ineligible_candidates"]) == 2
    with empty_factory._get_engine().connect() as connection:
        row = connection.execute(
            text(
                "SELECT top_technician_id, top_objective_score "
                "FROM scoring_evaluation_sets"
            )
        ).one()
        assert row == (None, None)
    empty_factory.dispose()


def test_policy_failure_rolls_back_configuration_and_preserves_sources(
    tmp_path: Path,
) -> None:
    path = tmp_path / "rollback-scoring.db"
    upgrade_to_head(path)
    factory = SqliteUnitOfWorkFactory(path)
    eligibility_id = _prepare_eligibility(factory)
    with factory._get_engine().connect() as connection:
        before = connection.execute(
            text(
                "SELECT input_json, output_json FROM "
                "eligibility_evaluation_sets WHERE id = :id"
            ),
            {"id": eligibility_id},
        ).one()

    class RaisingPolicy:
        def evaluate(self, **_):
            raise RuntimeError("private")

    command = ScoreEligibleTechnicians(
        unit_of_work_factory=factory,
        uuid_factory=lambda: UUID(
            "66666666-6666-4666-8666-666666666666"
        ),
        clock=lambda: datetime(2026, 7, 28, 12, 2, tzinfo=UTC),
        policy_factory=lambda: RaisingPolicy(),
    )
    with pytest.raises(ScoringPolicyFailure):
        command.execute(_request(eligibility_id))
    with factory._get_engine().connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM scoring_evaluation_sets")
        ).scalar_one() == 0
        assert connection.execute(
            text(
                "SELECT count(*) FROM configuration_versions "
                "WHERE version = 'scoring-v1'"
            )
        ).scalar_one() == 0
        after = connection.execute(
            text(
                "SELECT input_json, output_json FROM "
                "eligibility_evaluation_sets WHERE id = :id"
            ),
            {"id": eligibility_id},
        ).one()
        assert after == before
    factory.dispose()


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE scoring_evaluation_sets SET input_hash = '" + ("0" * 64) + "'",
        (
            "UPDATE scoring_evaluation_sets "
            "SET candidate_count = 3, ineligible_count = 2"
        ),
        (
            "UPDATE scoring_evaluation_sets SET output_json = "
            "json_set(output_json, '$.eligible_candidates[0].rank', 2)"
        ),
        (
            "UPDATE scoring_evaluation_sets "
            "SET created_at = '2026-07-28T12:02:00'"
        ),
    ],
)
def test_retained_scoring_corruption_fails_safely(
    tmp_path: Path,
    statement: str,
) -> None:
    path = tmp_path / "matrix-corrupt.db"
    upgrade_to_head(path)
    factory = SqliteUnitOfWorkFactory(path)
    eligibility_id = _prepare_eligibility(factory)
    command = ScoreEligibleTechnicians(
        unit_of_work_factory=factory,
        uuid_factory=lambda: UUID(
            "66666666-6666-4666-8666-666666666666"
        ),
        clock=lambda: datetime(2026, 7, 28, 12, 2, tzinfo=UTC),
    )
    command.execute(_request(eligibility_id))
    with factory._get_engine().begin() as connection:
        connection.execute(text(statement))
    with pytest.raises(ScoringPersistenceError):
        command.execute(_request(eligibility_id))
    factory.dispose()


def test_configuration_corruption_and_foreign_key_violation_fail(
    tmp_path: Path,
) -> None:
    path = tmp_path / "configuration-corrupt.db"
    upgrade_to_head(path)
    factory = SqliteUnitOfWorkFactory(path)
    eligibility_id = _prepare_eligibility(factory)
    command = ScoreEligibleTechnicians(
        unit_of_work_factory=factory,
        uuid_factory=lambda: UUID(
            "66666666-6666-4666-8666-666666666666"
        ),
        clock=lambda: datetime(2026, 7, 28, 12, 2, tzinfo=UTC),
    )
    first = command.execute(_request(eligibility_id))
    with factory._get_engine().begin() as connection:
        connection.execute(
            text(
                "UPDATE configuration_versions SET registry_json = '{}', "
                "registry_sha256 = :digest WHERE version = 'scoring-v1'"
            ),
            {"digest": "0" * 64},
        )
    with pytest.raises(ScoringPersistenceError):
        command.execute(_request(eligibility_id))

    with factory._get_engine().begin() as connection:
        with pytest.raises(IntegrityError):
            connection.execute(
                text(
                    "INSERT INTO scoring_evaluation_sets "
                    "(id, eligibility_evaluation_set_id, schema_version, "
                    "configuration_version, input_hash, input_json, "
                    "output_json, candidate_count, eligible_count, "
                    "ineligible_count, top_technician_id, "
                    "top_objective_score, created_at) "
                    "SELECT '99999999-9999-4999-8999-999999999999', "
                    "'88888888-8888-4888-8888-888888888888', "
                    "schema_version, configuration_version, input_hash, "
                    "input_json, output_json, candidate_count, eligible_count, "
                    "ineligible_count, top_technician_id, "
                    "top_objective_score, created_at "
                    "FROM scoring_evaluation_sets WHERE id = :id"
                ),
                {"id": first.evaluation_set_id},
            )
    factory.dispose()
