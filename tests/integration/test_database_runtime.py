from pathlib import Path
import sqlite3
import time

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError


def test_database_path_is_project_relative_not_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.adapters.persistence.database import PROJECT_ROOT, resolve_database_path

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SMART_DISPATCH_DB_PATH", raising=False)

    assert resolve_database_path() == PROJECT_ROOT / "data" / "smart_dispatch.db"


def test_each_connection_has_required_pragmas(tmp_path: Path) -> None:
    from app.adapters.persistence.database import BUSY_TIMEOUT_MS, create_sqlite_engine

    engine = create_sqlite_engine(tmp_path / "runtime.db")
    try:
        with engine.connect() as first, engine.connect() as second:
            assert (
                first.connection.driver_connection
                is not second.connection.driver_connection
            )
            for connection in (first, second):
                foreign_keys = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
                journal_mode = connection.execute(text("PRAGMA journal_mode")).scalar_one()
                busy_timeout = connection.execute(text("PRAGMA busy_timeout")).scalar_one()

                assert foreign_keys == 1
                assert journal_mode.lower() == "wal"
                assert busy_timeout == BUSY_TIMEOUT_MS == 5000
    finally:
        engine.dispose()


def test_raw_backup_connection_uses_required_pragmas(tmp_path: Path) -> None:
    from app.adapters.persistence.database import BUSY_TIMEOUT_MS, connect_sqlite

    database_path = tmp_path / "raw.db"
    with connect_sqlite(database_path) as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone() == (1,)
        assert connection.execute("PRAGMA journal_mode").fetchone() == ("wal",)
        assert connection.execute("PRAGMA busy_timeout").fetchone() == (
            BUSY_TIMEOUT_MS,
        )


def test_foreign_key_violation_is_rejected(tmp_path: Path) -> None:
    from app.adapters.persistence.database import create_sqlite_engine

    engine = create_sqlite_engine(tmp_path / "foreign-key.db")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE parents (id INTEGER PRIMARY KEY)"))
            connection.execute(
                text(
                    "CREATE TABLE children ("
                    "id INTEGER PRIMARY KEY, "
                    "parent_id INTEGER NOT NULL REFERENCES parents(id)"
                    ")"
                )
            )

        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    text("INSERT INTO children (id, parent_id) VALUES (1, 999)")
                )
    finally:
        engine.dispose()


def test_lock_contention_respects_configured_busy_timeout(tmp_path: Path) -> None:
    from app.adapters.persistence.database import BUSY_TIMEOUT_MS, create_sqlite_engine

    engine = create_sqlite_engine(tmp_path / "locked.db")
    locker = sqlite3.connect(tmp_path / "locked.db", timeout=0)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE sentinel (id INTEGER PRIMARY KEY)"))

        locker.execute("BEGIN EXCLUSIVE")
        started = time.monotonic()
        with pytest.raises(OperationalError):
            with engine.begin() as connection:
                connection.execute(text("INSERT INTO sentinel (id) VALUES (1)"))
        elapsed = time.monotonic() - started

        assert elapsed >= (BUSY_TIMEOUT_MS / 1000) * 0.8
        assert elapsed < (BUSY_TIMEOUT_MS / 1000) * 2
    finally:
        locker.rollback()
        locker.close()
        engine.dispose()


def test_sqlite_capability_floor_is_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.adapters.persistence import database

    monkeypatch.setattr(database.sqlite3, "sqlite_version", "3.34.9")

    with pytest.raises(database.DatabaseCapabilityError):
        database.validate_sqlite_capability()
