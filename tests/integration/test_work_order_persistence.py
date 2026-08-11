from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from app.adapters.persistence.database import create_sqlite_engine
from app.adapters.persistence.unit_of_work import SqliteUnitOfWorkFactory
from app.application.ports.persistence import PersistenceAdapterError
from app.application.commands.create_work_order import (
    CreateWorkOrder,
    CreateWorkOrderPersistenceError,
    CreateWorkOrderRequest,
    IdempotencyConflict,
)
from app.migrations.runtime import upgrade_to_head


NOW = datetime(2026, 7, 28, 15, 45, tzinfo=UTC)
RAW_INPUT = {
    "incident_text": "  Corte de energía  ",
    "address": "  Avenida 123  ",
    "zone": "  Norte  ",
    "context": {"source": "phone"},
}


def request(raw_input: dict | None = None) -> CreateWorkOrderRequest:
    return CreateWorkOrderRequest(
        raw_input=raw_input or RAW_INPUT,
        route="/api/v1/work-orders",
        idempotency_key="same-key",
        request_id="22222222-2222-4222-8222-222222222222",
    )


@pytest.fixture
def migrated_database(tmp_path: Path) -> Path:
    path = tmp_path / "work-orders.db"
    upgrade_to_head(path)
    return path


def test_real_uow_persists_exact_raw_values_and_replays(migrated_database: Path) -> None:
    factory = SqliteUnitOfWorkFactory(migrated_database)
    command = CreateWorkOrder(
        unit_of_work_factory=factory,
        uuid_factory=lambda: UUID("11111111-1111-4111-8111-111111111111"),
        clock=lambda: NOW,
    )

    first = command.execute(request())
    replay = command.execute(request())

    assert first.body == replay.body
    with factory() as unit_of_work:
        reconstructed = unit_of_work.work_orders.get(first.body["data"]["id"])
    assert reconstructed is not None
    assert reconstructed.raw_input == RAW_INPUT
    assert reconstructed.created_at == NOW
    engine = create_sqlite_engine(migrated_database)
    try:
        with engine.connect() as connection:
            work_order = connection.execute(
                text("SELECT * FROM work_orders")
            ).mappings().one()
            retained = connection.execute(
                text("SELECT * FROM idempotency_records")
            ).mappings().one()
        assert work_order["incident_text"] == RAW_INPUT["incident_text"]
        assert work_order["address"] == RAW_INPUT["address"]
        assert work_order["zone"] == RAW_INPUT["zone"]
        assert work_order["raw_input_json"] == (
            '{"address":"  Avenida 123  ","context":{"source":"phone"},'
            '"incident_text":"  Corte de energía  ","zone":"  Norte  "}'
        )
        assert work_order["context_json"] == '{"source":"phone"}'
        assert work_order["created_at"] == "2026-07-28T15:45:00Z"
        assert retained["response_status"] == 201
        assert retained["request_hash"]
    finally:
        engine.dispose()
        factory.dispose()


def test_repository_corruption_is_translated_to_typed_persistence_error(
    migrated_database: Path,
) -> None:
    factory = SqliteUnitOfWorkFactory(migrated_database)
    command = CreateWorkOrder(
        unit_of_work_factory=factory,
        uuid_factory=uuid4,
        clock=lambda: NOW,
    )
    result = command.execute(request())
    engine = create_sqlite_engine(migrated_database)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE work_orders SET raw_input_json = '{' WHERE id = :id"),
                {"id": result.body["data"]["id"]},
            )
    finally:
        engine.dispose()

    with pytest.raises(PersistenceAdapterError):
        with factory() as unit_of_work:
            unit_of_work.work_orders.get(result.body["data"]["id"])

    factory.dispose()


def test_corrupted_idempotency_timestamp_maps_to_command_failure(
    migrated_database: Path,
) -> None:
    factory = SqliteUnitOfWorkFactory(migrated_database)
    command = CreateWorkOrder(
        unit_of_work_factory=factory,
        uuid_factory=uuid4,
        clock=lambda: NOW,
    )
    command.execute(request())
    engine = create_sqlite_engine(migrated_database)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE idempotency_records SET created_at = 'not-a-time'")
            )
    finally:
        engine.dispose()

    with pytest.raises(CreateWorkOrderPersistenceError):
        command.execute(request())

    factory.dispose()


def test_changed_hash_conflicts_without_mutation(migrated_database: Path) -> None:
    factory = SqliteUnitOfWorkFactory(migrated_database)
    command = CreateWorkOrder(
        unit_of_work_factory=factory,
        uuid_factory=uuid4,
        clock=lambda: NOW,
    )
    command.execute(request())

    with pytest.raises(IdempotencyConflict):
        command.execute(request({**RAW_INPUT, "zone": "Sur"}))

    engine = create_sqlite_engine(migrated_database)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM work_orders")).scalar_one() == 1
            assert connection.execute(
                text("SELECT count(*) FROM idempotency_records")
            ).scalar_one() == 1
    finally:
        engine.dispose()
        factory.dispose()


def test_idempotency_insert_failure_rolls_back_work_order(migrated_database: Path) -> None:
    engine = create_sqlite_engine(migrated_database)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TRIGGER reject_idempotency BEFORE INSERT "
                    "ON idempotency_records BEGIN "
                    "SELECT RAISE(ABORT, 'injected failure'); END"
                )
            )
    finally:
        engine.dispose()
    factory = SqliteUnitOfWorkFactory(migrated_database)
    command = CreateWorkOrder(
        unit_of_work_factory=factory,
        uuid_factory=uuid4,
        clock=lambda: NOW,
    )

    with pytest.raises(CreateWorkOrderPersistenceError):
        command.execute(request())

    engine = create_sqlite_engine(migrated_database)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM work_orders")).scalar_one() == 0
            assert connection.execute(
                text("SELECT count(*) FROM idempotency_records")
            ).scalar_one() == 0
    finally:
        engine.dispose()
        factory.dispose()


def test_concurrent_identical_requests_converge_on_one_result(
    migrated_database: Path,
) -> None:
    factory = SqliteUnitOfWorkFactory(migrated_database)

    def execute_once(_: int):
        return CreateWorkOrder(
            unit_of_work_factory=factory,
            uuid_factory=uuid4,
            clock=lambda: NOW,
        ).execute(request())

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(execute_once, range(2)))

    assert results[0].body == results[1].body
    engine = create_sqlite_engine(migrated_database)
    try:
        with engine.connect() as connection:
            assert connection.execute(text("SELECT count(*) FROM work_orders")).scalar_one() == 1
            assert connection.execute(
                text("SELECT count(*) FROM idempotency_records")
            ).scalar_one() == 1
    finally:
        engine.dispose()
        factory.dispose()
