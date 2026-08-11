from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import pytest

from app.adapters.persistence.unit_of_work import SqliteUnitOfWorkFactory
from app.adapters.stages.deterministic_analyze import DeterministicAnalyzeStage
from app.application.commands.analyze_work_order import (
    AnalyzeWorkOrder,
    AnalyzeWorkOrderRequest,
)
from app.application.commands.determine_technician_eligibility import (
    DetermineTechnicianEligibility,
    DetermineTechnicianEligibilityRequest,
    EligibilityPersistenceError,
    InvalidEligibilityOutput,
)
from app.domain.eligibility.models import (
    EligibilityCandidate,
    EligibilityResult,
)
from app.domain.work_orders.models import WorkOrder
from app.migrations.runtime import upgrade_to_head


WORK_ORDER_ID = "11111111-1111-4111-8111-111111111111"


def _prepare_analysis(factory: SqliteUnitOfWorkFactory) -> str:
    work_order = WorkOrder(
        id=UUID("11111111-1111-4111-8111-111111111111"),
        schema_version="v1",
        raw_input={
            "incident_text": "Fuga de gas",
            "address": "Calle privada",
            "zone": "Centro",
            "context": None,
        },
        incident_text="Fuga de gas",
        address="Calle privada",
        zone="Centro",
        context=None,
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )
    with factory() as uow:
        uow.work_orders.add(work_order)
    return AnalyzeWorkOrder(
        unit_of_work_factory=factory,
        stage=DeterministicAnalyzeStage(),
        uuid_factory=lambda: UUID("22222222-2222-4222-8222-222222222222"),
        clock=lambda: datetime(2026, 7, 28, 12, tzinfo=UTC),
    ).execute(
        AnalyzeWorkOrderRequest(work_order_id=str(work_order.id))
    ).analysis_id


def _technician(travel_minutes: int = 30) -> dict:
    return {
        "technician_id": "33333333-3333-4333-8333-333333333333",
        "availability": "available",
        "certifications": ["gas_registered"],
        "shift_start": "2026-07-28T08:00:00Z",
        "shift_end": "2026-07-28T16:00:00Z",
        "assigned_work_minutes": 300,
        "accumulated_driving_minutes": 120,
        "has_required_epp": True,
        "estimated_travel_minutes": travel_minutes,
        "distance_meters": 60_000,
    }


def test_real_sqlite_eligibility_round_trip_replay_and_changed_input(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "eligibility.db"
    upgrade_to_head(database_path)
    factory = SqliteUnitOfWorkFactory(database_path)
    analysis_id = _prepare_analysis(factory)
    ids = iter(
        [
            UUID("44444444-4444-4444-8444-444444444444"),
            UUID("55555555-5555-4555-8555-555555555555"),
        ]
    )
    command = DetermineTechnicianEligibility(
        unit_of_work_factory=factory,
        uuid_factory=lambda: next(ids),
        clock=lambda: datetime(2026, 7, 28, 12, 1, tzinfo=UTC),
    )

    first = command.execute(
        DetermineTechnicianEligibilityRequest(
            analysis_id=analysis_id,
            captured_at=datetime(2026, 7, 28, 12, tzinfo=UTC),
            technicians=(_technician(),),
        )
    )
    replay = command.execute(
        DetermineTechnicianEligibilityRequest(
            analysis_id=analysis_id,
            captured_at=datetime(2026, 7, 28, 12, tzinfo=UTC),
            technicians=(_technician(),),
        )
    )
    changed = command.execute(
        DetermineTechnicianEligibilityRequest(
            analysis_id=analysis_id,
            captured_at=datetime(2026, 7, 28, 12, tzinfo=UTC),
            technicians=(_technician(31),),
        )
    )

    assert first.replayed is False
    assert replay.replayed is True
    assert replay.evaluation_set_id == first.evaluation_set_id
    assert changed.evaluation_set_id != first.evaluation_set_id
    with factory._get_engine().connect() as connection:
        row = connection.execute(
            text(
                "SELECT candidate_count, eligible_count, ineligible_count, "
                "no_feasible_candidates FROM eligibility_evaluation_sets "
                "ORDER BY id LIMIT 1"
            )
        ).one()
        assert tuple(row) == (1, 1, 0, 0)
        assert connection.execute(
            text("SELECT count(*) FROM eligibility_evaluation_sets")
        ).scalar_one() == 2
    factory.dispose()


def test_empty_roster_persists_no_feasible_evidence(tmp_path: Path) -> None:
    database_path = tmp_path / "empty.db"
    upgrade_to_head(database_path)
    factory = SqliteUnitOfWorkFactory(database_path)
    analysis_id = _prepare_analysis(factory)
    result = DetermineTechnicianEligibility(
        unit_of_work_factory=factory,
        uuid_factory=lambda: UUID("44444444-4444-4444-8444-444444444444"),
        clock=lambda: datetime(2026, 7, 28, 12, 1, tzinfo=UTC),
    ).execute(
        DetermineTechnicianEligibilityRequest(
            analysis_id=analysis_id,
            captured_at=datetime(2026, 7, 28, 12, tzinfo=UTC),
            technicians=(),
        )
    )

    assert result.output["no_feasible_candidates"] is True
    assert result.output["candidates"] == []
    factory.dispose()


def test_corrupt_summary_is_rejected_on_replay(tmp_path: Path) -> None:
    database_path = tmp_path / "corrupt.db"
    upgrade_to_head(database_path)
    factory = SqliteUnitOfWorkFactory(database_path)
    analysis_id = _prepare_analysis(factory)
    request = DetermineTechnicianEligibilityRequest(
        analysis_id=analysis_id,
        captured_at=datetime(2026, 7, 28, 12, tzinfo=UTC),
        technicians=(_technician(),),
    )
    command = DetermineTechnicianEligibility(
        unit_of_work_factory=factory,
        uuid_factory=lambda: UUID("44444444-4444-4444-8444-444444444444"),
        clock=lambda: datetime(2026, 7, 28, 12, 1, tzinfo=UTC),
    )
    command.execute(request)
    with factory._get_engine().begin() as connection:
        connection.exec_driver_sql("PRAGMA ignore_check_constraints = ON")
        connection.execute(
            text(
                "UPDATE eligibility_evaluation_sets "
                "SET candidate_count = 2"
            )
        )

    with pytest.raises(EligibilityPersistenceError):
        command.execute(request)
    factory.dispose()


def test_corrupt_input_hash_cannot_be_hidden_by_inserting_replacement(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "corrupt-hash.db"
    upgrade_to_head(database_path)
    factory = SqliteUnitOfWorkFactory(database_path)
    analysis_id = _prepare_analysis(factory)
    identifiers = iter(
        [
            UUID("44444444-4444-4444-8444-444444444444"),
            UUID("55555555-5555-4555-8555-555555555555"),
        ]
    )
    command = DetermineTechnicianEligibility(
        unit_of_work_factory=factory,
        uuid_factory=lambda: next(identifiers),
        clock=lambda: datetime(2026, 7, 28, 12, 1, tzinfo=UTC),
    )
    request = DetermineTechnicianEligibilityRequest(
        analysis_id=analysis_id,
        captured_at=datetime(2026, 7, 28, 12, tzinfo=UTC),
        technicians=(_technician(),),
    )
    command.execute(request)
    with factory._get_engine().begin() as connection:
        connection.exec_driver_sql("PRAGMA ignore_check_constraints = ON")
        connection.execute(
            text(
                "UPDATE eligibility_evaluation_sets "
                "SET input_hash = :value"
            ),
            {"value": "f" * 64},
        )

    with pytest.raises(EligibilityPersistenceError):
        command.execute(request)
    with factory._get_engine().connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM eligibility_evaluation_sets")
        ).scalar_one() == 1
    factory.dispose()


def test_naive_retained_creation_timestamp_is_rejected(tmp_path: Path) -> None:
    database_path = tmp_path / "naive-time.db"
    upgrade_to_head(database_path)
    factory = SqliteUnitOfWorkFactory(database_path)
    analysis_id = _prepare_analysis(factory)
    request = DetermineTechnicianEligibilityRequest(
        analysis_id=analysis_id,
        captured_at=datetime(2026, 7, 28, 12, tzinfo=UTC),
        technicians=(_technician(),),
    )
    command = DetermineTechnicianEligibility(
        unit_of_work_factory=factory,
        uuid_factory=lambda: UUID("44444444-4444-4444-8444-444444444444"),
        clock=lambda: datetime(2026, 7, 28, 12, 1, tzinfo=UTC),
    )
    command.execute(request)
    with factory._get_engine().begin() as connection:
        connection.execute(
            text(
                "UPDATE eligibility_evaluation_sets "
                "SET created_at = '2026-07-28T12:01:00'"
            )
        )

    with pytest.raises(EligibilityPersistenceError):
        command.execute(request)
    factory.dispose()


def test_changed_work_order_invalidates_retained_analysis_source(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "changed-source.db"
    upgrade_to_head(database_path)
    factory = SqliteUnitOfWorkFactory(database_path)
    analysis_id = _prepare_analysis(factory)
    with factory._get_engine().begin() as connection:
        connection.execute(
            text(
                "UPDATE work_orders SET incident_text = :text, "
                "raw_input_json = :raw"
            ),
            {
                "text": "Corte eléctrico",
                "raw": (
                    '{"address":"Calle privada","context":null,'
                    '"incident_text":"Corte eléctrico","zone":"Centro"}'
                ),
            },
        )

    with pytest.raises(EligibilityPersistenceError):
        DetermineTechnicianEligibility(
            unit_of_work_factory=factory,
            uuid_factory=lambda: UUID(
                "44444444-4444-4444-8444-444444444444"
            ),
            clock=lambda: datetime(2026, 7, 28, 12, 1, tzinfo=UTC),
        ).execute(
            DetermineTechnicianEligibilityRequest(
                analysis_id=analysis_id,
                captured_at=datetime(2026, 7, 28, 12, tzinfo=UTC),
                technicians=(_technician(),),
            )
        )
    factory.dispose()


class _MalformedPolicy:
    def evaluate(self, **kwargs):
        candidate = EligibilityCandidate(
            technician_id=UUID("33333333-3333-4333-8333-333333333333"),
            eligible=True,
            distance_meters=0,
            checks=(),
            warnings=(),
        )
        return EligibilityResult(
            schema_version="v1",
            configuration_version="eligibility-v1",
            candidates=(candidate,),
            eligible_technician_ids=(candidate.technician_id,),
            ineligible_technician_ids=(),
            no_feasible_candidates=False,
        )


def test_invalid_output_rolls_back_only_new_eligibility_writes(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "rollback.db"
    upgrade_to_head(database_path)
    factory = SqliteUnitOfWorkFactory(database_path)
    analysis_id = _prepare_analysis(factory)
    command = DetermineTechnicianEligibility(
        unit_of_work_factory=factory,
        uuid_factory=lambda: UUID("44444444-4444-4444-8444-444444444444"),
        clock=lambda: datetime(2026, 7, 28, 12, 1, tzinfo=UTC),
        policy_factory=lambda: _MalformedPolicy(),
    )

    with pytest.raises(InvalidEligibilityOutput):
        command.execute(
            DetermineTechnicianEligibilityRequest(
                analysis_id=analysis_id,
                captured_at=datetime(2026, 7, 28, 12, tzinfo=UTC),
                technicians=(_technician(),),
            )
        )

    with factory._get_engine().connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM work_order_analyses")
        ).scalar_one() == 1
        assert connection.execute(
            text(
                "SELECT count(*) FROM configuration_versions "
                "WHERE version = 'eligibility-v1'"
            )
        ).scalar_one() == 0
        assert connection.execute(
            text("SELECT count(*) FROM eligibility_evaluation_sets")
        ).scalar_one() == 0
    factory.dispose()


def test_eligibility_foreign_keys_reject_orphan_evidence(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "foreign-key.db"
    upgrade_to_head(database_path)
    factory = SqliteUnitOfWorkFactory(database_path)
    with pytest.raises(IntegrityError):
        with factory._get_engine().begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO eligibility_evaluation_sets "
                    "(id, work_order_id, work_order_analysis_id, "
                    "schema_version, configuration_version, input_hash, "
                    "input_json, output_json, candidate_count, eligible_count, "
                    "ineligible_count, no_feasible_candidates, created_at) "
                    "VALUES (:id, :work_order_id, :analysis_id, 'v1', "
                    "'eligibility-v1', :input_hash, '{}', '{}', 0, 0, 0, 1, "
                    "'2026-07-28T12:00:00Z')"
                ),
                {
                    "id": "44444444-4444-4444-8444-444444444444",
                    "work_order_id": WORK_ORDER_ID,
                    "analysis_id": "22222222-2222-4222-8222-222222222222",
                    "input_hash": "a" * 64,
                },
            )
    factory.dispose()


def test_composite_foreign_key_rejects_analysis_work_order_mismatch(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "composite-foreign-key.db"
    upgrade_to_head(database_path)
    factory = SqliteUnitOfWorkFactory(database_path)
    analysis_id = _prepare_analysis(factory)
    command = DetermineTechnicianEligibility(
        unit_of_work_factory=factory,
        uuid_factory=lambda: UUID("44444444-4444-4444-8444-444444444444"),
        clock=lambda: datetime(2026, 7, 28, 12, 1, tzinfo=UTC),
    )
    command.execute(
        DetermineTechnicianEligibilityRequest(
            analysis_id=analysis_id,
            captured_at=datetime(2026, 7, 28, 12, tzinfo=UTC),
            technicians=(_technician(),),
        )
    )
    other = WorkOrder(
        id=UUID("66666666-6666-4666-8666-666666666666"),
        schema_version="v1",
        raw_input={
            "incident_text": "Inspección",
            "address": "Calle 2",
            "zone": "Norte",
            "context": None,
        },
        incident_text="Inspección",
        address="Calle 2",
        zone="Norte",
        context=None,
        created_at=datetime(2026, 7, 28, tzinfo=UTC),
    )
    with factory() as unit_of_work:
        unit_of_work.work_orders.add(other)

    with pytest.raises(IntegrityError):
        with factory._get_engine().begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO eligibility_evaluation_sets "
                    "SELECT :id, :work_order_id, work_order_analysis_id, "
                    "schema_version, configuration_version, input_hash, "
                    "input_json, output_json, candidate_count, eligible_count, "
                    "ineligible_count, no_feasible_candidates, created_at "
                    "FROM eligibility_evaluation_sets LIMIT 1"
                ),
                {
                    "id": "77777777-7777-4777-8777-777777777777",
                    "work_order_id": str(other.id),
                },
            )
    factory.dispose()
