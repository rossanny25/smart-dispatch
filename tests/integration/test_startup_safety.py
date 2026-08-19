from hashlib import sha256
import multiprocessing
import os
from pathlib import Path
import sqlite3
import time

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEARNING_STORE = PROJECT_ROOT / "data" / "learning_store.json"
PRODUCTION_VERSIONS = PROJECT_ROOT / "app" / "migrations" / "versions"
TEST_MIGRATIONS = PROJECT_ROOT / "tests" / "fixtures" / "migrations"


def create_sentinel_database(path: Path, value: str = "before") -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE sentinel (value TEXT NOT NULL)")
        connection.execute("INSERT INTO sentinel (value) VALUES (?)", (value,))


def read_sentinel(path: Path) -> str:
    with sqlite3.connect(path) as connection:
        return connection.execute("SELECT value FROM sentinel").fetchone()[0]


def build_test_migration_config(database_path: Path, fixture: str) -> Config:
    from app.migrations.runtime import build_alembic_config

    config = build_alembic_config(database_path)
    config.set_main_option(
        "version_locations",
        os.pathsep.join(
            (str(PRODUCTION_VERSIONS), str(TEST_MIGRATIONS / fixture))
        ),
    )
    return config


def make_test_pending_checker(fixture: str):
    def check(database_path: Path) -> bool:
        from app.adapters.persistence.database import create_sqlite_engine

        config = build_test_migration_config(database_path, fixture)
        head = ScriptDirectory.from_config(config).get_current_head()
        engine = create_sqlite_engine(database_path)
        try:
            with engine.connect() as connection:
                current = MigrationContext.configure(connection).get_current_revision()
        finally:
            engine.dispose()
        return current != head

    return check


def make_test_migration_runner(fixture: str):
    def migrate(database_path: Path) -> None:
        from app.adapters.persistence.database import create_sqlite_engine

        config = build_test_migration_config(database_path, fixture)
        engine = create_sqlite_engine(database_path)
        try:
            with engine.begin() as connection:
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
        finally:
            engine.dispose()

    return migrate


def hold_startup_lock(database_path: Path, marker_path: Path) -> None:
    from app.startup import _startup_lock

    with _startup_lock(database_path):
        marker_path.write_text("locked", encoding="utf-8")
        time.sleep(0.8)


def measure_startup_lock_wait(
    database_path: Path,
    result_queue: multiprocessing.Queue,
) -> None:
    from app.startup import _startup_lock

    started = time.monotonic()
    with _startup_lock(database_path):
        result_queue.put(time.monotonic() - started)


def test_backup_is_integrity_checked_and_restores_pre_migration_data(
    tmp_path: Path,
) -> None:
    from app.adapters.persistence.backup import (
        create_verified_backup,
        restore_verified_backup,
        verify_database_integrity,
    )

    database_path = tmp_path / "runtime.db"
    create_sentinel_database(database_path)

    backup_path = create_verified_backup(database_path, tmp_path / "backups")
    with sqlite3.connect(database_path) as connection:
        connection.execute("UPDATE sentinel SET value = 'after'")

    assert backup_path != database_path
    assert verify_database_integrity(backup_path)
    restore_verified_backup(backup_path, database_path)
    assert read_sentinel(database_path) == "before"


def test_backup_names_are_collision_safe(tmp_path: Path) -> None:
    from app.adapters.persistence.backup import create_verified_backup

    database_path = tmp_path / "runtime.db"
    create_sentinel_database(database_path)

    first = create_verified_backup(database_path, tmp_path / "backups")
    second = create_verified_backup(database_path, tmp_path / "backups")

    assert first != second
    assert first.exists()
    assert second.exists()


def test_failed_migration_restores_or_preserves_sentinel_and_never_starts_uvicorn(
    tmp_path: Path,
) -> None:
    from app.runtime import StartupError, run
    from app.startup import prepare_runtime

    database_path = tmp_path / "runtime.db"
    create_sentinel_database(database_path)
    server_started = False

    def mark_server_started(*args: object, **kwargs: object) -> None:
        nonlocal server_started
        server_started = True

    before = sha256(LEARNING_STORE.read_bytes()).hexdigest()
    with pytest.raises(StartupError, match="Alembic upgrade to head"):
        run(
            prepare=lambda: prepare_runtime(
                database_path=database_path,
                backup_dir=tmp_path / "backups",
                pending_checker=make_test_pending_checker("failure"),
                migration_runner=make_test_migration_runner("failure"),
            ),
            serve=mark_server_started,
        )

    assert not server_started
    assert read_sentinel(database_path) == "before"
    with sqlite3.connect(database_path) as connection:
        objects = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%'"
            )
        }
    assert objects == {"sentinel"}
    assert sha256(LEARNING_STORE.read_bytes()).hexdigest() == before


def test_existing_pending_database_is_backed_up_before_real_successful_upgrade(
    tmp_path: Path,
) -> None:
    from app.runtime import run
    from app.startup import prepare_runtime

    database_path = tmp_path / "pending-success.db"
    backup_dir = tmp_path / "backups"
    create_sentinel_database(database_path)
    before = sha256(LEARNING_STORE.read_bytes()).hexdigest()
    server_started_after_head = False

    def prove_head_before_serve(*args: object, **kwargs: object) -> None:
        nonlocal server_started_after_head
        assert not make_test_pending_checker("success")(database_path)
        with sqlite3.connect(database_path) as connection:
            assert connection.execute(
                "SELECT value FROM review_migration_marker"
            ).fetchone() == ("migrated",)
        server_started_after_head = True

    run(
        prepare=lambda: prepare_runtime(
            database_path=database_path,
            backup_dir=backup_dir,
            pending_checker=make_test_pending_checker("success"),
            migration_runner=make_test_migration_runner("success"),
        ),
        serve=prove_head_before_serve,
    )

    backups = list(backup_dir.glob("*.backup.db"))
    assert server_started_after_head
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert connection.execute("SELECT value FROM sentinel").fetchone() == ("before",)
        names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%'"
            )
        }
    assert names == {"sentinel"}
    assert sha256(LEARNING_STORE.read_bytes()).hexdigest() == before


def test_fresh_database_migrates_without_unnecessary_backup(tmp_path: Path) -> None:
    from app.startup import prepare_runtime

    database_path = tmp_path / "fresh.db"
    backup_dir = tmp_path / "backups"

    prepare_runtime(database_path=database_path, backup_dir=backup_dir)

    assert database_path.exists()
    assert not backup_dir.exists() or not list(backup_dir.iterdir())


def test_failed_first_migration_removes_partial_fresh_database(tmp_path: Path) -> None:
    from app.startup import StartupError, prepare_runtime

    database_path = tmp_path / "fresh-failure.db"

    def fail_after_creating_schema(path: Path) -> None:
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TABLE partial (value TEXT)")
        raise RuntimeError("revision fresh_failure")

    with pytest.raises(StartupError, match="Alembic upgrade to head"):
        prepare_runtime(
            database_path=database_path,
            backup_dir=tmp_path / "backups",
            pending_checker=lambda _: True,
            migration_runner=fail_after_creating_schema,
        )

    assert not database_path.exists()
    assert not Path(f"{database_path}-wal").exists()
    assert not Path(f"{database_path}-shm").exists()


def test_interrupted_migration_restores_verified_backup(tmp_path: Path) -> None:
    from app.startup import prepare_runtime

    database_path = tmp_path / "interrupted.db"
    create_sentinel_database(database_path)

    def interrupt_after_mutation(path: Path) -> None:
        with sqlite3.connect(path) as connection:
            connection.execute("UPDATE sentinel SET value = 'interrupted'")
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        prepare_runtime(
            database_path=database_path,
            backup_dir=tmp_path / "backups",
            pending_checker=lambda _: True,
            migration_runner=interrupt_after_mutation,
        )

    assert read_sentinel(database_path) == "before"


def test_startup_lock_serializes_independent_processes(tmp_path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    database_path = tmp_path / "shared.db"
    marker_path = tmp_path / "lock-held"
    result_queue = context.Queue()
    holder = context.Process(
        target=hold_startup_lock,
        args=(database_path, marker_path),
    )
    holder.start()
    deadline = time.monotonic() + 3
    while not marker_path.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert marker_path.exists()

    waiter = context.Process(
        target=measure_startup_lock_wait,
        args=(database_path, result_queue),
    )
    waiter.start()
    holder.join(timeout=3)
    waiter.join(timeout=3)

    assert holder.exitcode == waiter.exitcode == 0
    assert result_queue.get(timeout=1) >= 0.2


def test_learning_store_is_byte_preserved_across_startup(tmp_path: Path) -> None:
    from app.startup import StartupError
    from app.startup import prepare_runtime

    before = sha256(LEARNING_STORE.read_bytes()).hexdigest()
    prepare_runtime(database_path=tmp_path / "runtime.db", backup_dir=tmp_path / "backups")
    failing_database = tmp_path / "failing.db"
    create_sentinel_database(failing_database)

    with pytest.raises(StartupError):
        prepare_runtime(
            database_path=failing_database,
            backup_dir=tmp_path / "backups",
            pending_checker=lambda _: True,
            migration_runner=lambda _: (_ for _ in ()).throw(
                RuntimeError("revision failure")
            ),
        )

    after = sha256(LEARNING_STORE.read_bytes()).hexdigest()

    assert after == before
