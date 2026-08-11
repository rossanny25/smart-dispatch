from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
import pytest

from app.adapters.persistence.unit_of_work import SqliteUnitOfWorkFactory
from app.adapters.stages.deterministic_analyze import DeterministicAnalyzeStage
from app.application.commands.analyze_work_order import (
    AnalyzePersistenceError,
    AnalyzeWorkOrder,
    AnalyzeWorkOrderRequest,
    InvalidAnalyzeOutput,
)
from app.domain.analysis.rules import ANALYSIS_REGISTRY_SHA256
from app.domain.work_orders.models import WorkOrder
from app.migrations.runtime import upgrade_to_head


def test_real_sqlite_analysis_round_trip_and_work_order_immutability(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "analysis.db"
    upgrade_to_head(database_path)
    factory = SqliteUnitOfWorkFactory(database_path)
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

    command = AnalyzeWorkOrder(
        unit_of_work_factory=factory,
        stage=DeterministicAnalyzeStage(),
        uuid_factory=lambda: UUID("22222222-2222-4222-8222-222222222222"),
        clock=lambda: datetime(2026, 7, 28, 12, tzinfo=UTC),
    )
    result = command.execute(AnalyzeWorkOrderRequest(work_order_id=str(work_order.id)))
    replay = command.execute(AnalyzeWorkOrderRequest(work_order_id=str(work_order.id)))

    assert result.output["requirements"]["category"] == "gas"
    assert replay.replayed is True
    engine = factory._get_engine()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM work_orders")).scalar_one() == 1
        assert connection.execute(
            text("SELECT count(*) FROM work_order_analyses")
        ).scalar_one() == 1
        assert connection.execute(
            text("SELECT incident_text FROM work_orders")
        ).scalar_one() == "Fuga de gas"
    factory.dispose()


class InvalidStage:
    def execute(self, payload):
        return {"schema_version": "v1"}


def _stored_work_order() -> WorkOrder:
    return WorkOrder(
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


def _command(factory, stage=None) -> AnalyzeWorkOrder:
    return AnalyzeWorkOrder(
        unit_of_work_factory=factory,
        stage=stage or DeterministicAnalyzeStage(),
        uuid_factory=lambda: UUID("22222222-2222-4222-8222-222222222222"),
        clock=lambda: datetime(2026, 7, 28, 12, tzinfo=UTC),
    )


def test_invalid_output_rolls_back_configuration_and_analysis(tmp_path: Path) -> None:
    database_path = tmp_path / "invalid.db"
    upgrade_to_head(database_path)
    factory = SqliteUnitOfWorkFactory(database_path)
    work_order = _stored_work_order()
    with factory() as uow:
        uow.work_orders.add(work_order)

    with pytest.raises(InvalidAnalyzeOutput):
        _command(factory, InvalidStage()).execute(
            AnalyzeWorkOrderRequest(work_order_id=str(work_order.id))
        )

    engine = factory._get_engine()
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT count(*) FROM configuration_versions")
        ).scalar_one() == 0
        assert connection.execute(
            text("SELECT count(*) FROM work_order_analyses")
        ).scalar_one() == 0
        assert connection.execute(
            text("SELECT raw_input_json FROM work_orders")
        ).scalar_one() == (
            '{"address":"Calle privada","context":null,'
            '"incident_text":"Fuga de gas","zone":"Centro"}'
        )
    factory.dispose()


def test_configuration_digest_and_corrupt_retained_output_are_guarded(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "corrupt.db"
    upgrade_to_head(database_path)
    factory = SqliteUnitOfWorkFactory(database_path)
    work_order = _stored_work_order()
    with factory() as uow:
        uow.work_orders.add(work_order)
    request = AnalyzeWorkOrderRequest(work_order_id=str(work_order.id))
    _command(factory).execute(request)

    engine = factory._get_engine()
    with engine.begin() as connection:
        assert connection.execute(
            text("SELECT registry_sha256 FROM configuration_versions")
        ).scalar_one() == ANALYSIS_REGISTRY_SHA256
        connection.execute(
            text("UPDATE work_order_analyses SET output_json = :output_json"),
            {"output_json": '{"bad":true}'},
        )

    with pytest.raises(AnalyzePersistenceError):
        _command(factory).execute(request)
    factory.dispose()


def test_analysis_foreign_keys_reject_orphan_evidence(tmp_path: Path) -> None:
    database_path = tmp_path / "foreign-key.db"
    upgrade_to_head(database_path)
    factory = SqliteUnitOfWorkFactory(database_path)
    engine = factory._get_engine()
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO work_order_analyses "
                    "(id, work_order_id, schema_version, configuration_version, "
                    "input_hash, output_json, category, priority, "
                    "sla_target_minutes, required_certifications_json, "
                    "estimated_service_duration_minutes, created_at) VALUES "
                    "(:id, :work_order_id, 'v1', 'analysis-v1', :input_hash, "
                    ":output_json, 'gas', 5, 60, :certifications, 90, :created_at)"
                ),
                {
                    "id": "22222222-2222-4222-8222-222222222222",
                    "work_order_id": "11111111-1111-4111-8111-111111111111",
                    "input_hash": "a" * 64,
                    "output_json": "{}",
                    "certifications": "[]",
                    "created_at": "2026-07-28T12:00:00Z",
                },
            )
    factory.dispose()


@pytest.mark.parametrize(
    ("statement", "parameters"),
    [
        (
            "UPDATE configuration_versions SET registry_sha256 = :value",
            {"value": "0" * 64},
        ),
        (
            "UPDATE work_order_analyses SET input_hash = :value",
            {"value": "f" * 64},
        ),
        (
            "UPDATE work_order_analyses SET category = :value",
            {"value": "maintenance"},
        ),
    ],
)
def test_replay_rejects_corrupt_configuration_input_or_columns(
    tmp_path: Path,
    statement: str,
    parameters: dict,
) -> None:
    database_path = tmp_path / "replay-corrupt.db"
    upgrade_to_head(database_path)
    factory = SqliteUnitOfWorkFactory(database_path)
    work_order = _stored_work_order()
    with factory() as uow:
        uow.work_orders.add(work_order)
    request = AnalyzeWorkOrderRequest(work_order_id=str(work_order.id))
    _command(factory).execute(request)
    with factory._get_engine().begin() as connection:
        connection.execute(text(statement), parameters)

    with pytest.raises(AnalyzePersistenceError):
        _command(factory).execute(request)
    factory.dispose()


def test_database_checks_reject_invalid_analysis_category(tmp_path: Path) -> None:
    database_path = tmp_path / "checks.db"
    upgrade_to_head(database_path)
    factory = SqliteUnitOfWorkFactory(database_path)
    work_order = _stored_work_order()
    with factory() as uow:
        uow.work_orders.add(work_order)
    _command(factory).execute(
        AnalyzeWorkOrderRequest(work_order_id=str(work_order.id))
    )

    with pytest.raises(IntegrityError):
        with factory._get_engine().begin() as connection:
            connection.execute(
                text("UPDATE work_order_analyses SET category = 'invented'")
            )
    factory.dispose()
