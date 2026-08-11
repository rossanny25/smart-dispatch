"""SQLite connection policy for the local single-process runtime."""

import os
from pathlib import Path
import sqlite3

from sqlalchemy import Engine, URL, create_engine, event


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "smart_dispatch.db"
DATABASE_PATH_ENV = "SMART_DISPATCH_DB_PATH"
BUSY_TIMEOUT_MS = 5000
MINIMUM_SQLITE_VERSION = (3, 35, 0)


class DatabaseCapabilityError(RuntimeError):
    """The bundled SQLite runtime cannot satisfy the architecture contract."""


def resolve_database_path(database_path: str | Path | None = None) -> Path:
    selected = database_path or os.environ.get(DATABASE_PATH_ENV)
    if selected is None:
        return DEFAULT_DATABASE_PATH

    path = Path(selected)
    return path if path.is_absolute() else PROJECT_ROOT / path


def validate_sqlite_capability() -> None:
    current = tuple(int(part) for part in sqlite3.sqlite_version.split("."))
    if current < MINIMUM_SQLITE_VERSION:
        raise DatabaseCapabilityError(
            "SQLite 3.35.0 or newer is required for Smart Dispatch IA."
        )


def configure_sqlite_connection(
    dbapi_connection: sqlite3.Connection,
) -> None:
    """Apply and verify the binding SQLite policy on one physical connection."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        journal_mode = cursor.execute("PRAGMA journal_mode=WAL").fetchone()
        cursor.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
        foreign_keys = cursor.execute("PRAGMA foreign_keys").fetchone()
        busy_timeout = cursor.execute("PRAGMA busy_timeout").fetchone()
    finally:
        cursor.close()

    if foreign_keys != (1,):
        raise DatabaseCapabilityError("SQLite foreign-key enforcement is unavailable.")
    if journal_mode is None or str(journal_mode[0]).lower() != "wal":
        raise DatabaseCapabilityError("SQLite WAL journal mode could not be enabled.")
    if busy_timeout != (BUSY_TIMEOUT_MS,):
        raise DatabaseCapabilityError("SQLite busy timeout could not be configured.")


def _configure_connection(
    dbapi_connection: sqlite3.Connection,
    _connection_record: object,
) -> None:
    configure_sqlite_connection(dbapi_connection)


def sqlite_url(database_path: str | Path | None = None) -> URL:
    """Build a URL without treating legal filename characters as URL syntax."""
    return URL.create(
        "sqlite+pysqlite",
        database=str(resolve_database_path(database_path)),
    )


def connect_sqlite(
    database_path: str | Path,
    *,
    read_only: bool = False,
) -> sqlite3.Connection:
    """Open a raw SQLite connection with the same policy as SQLAlchemy."""
    path = Path(database_path).resolve()
    target: str | Path
    if read_only:
        target = f"{path.as_uri()}?mode=ro"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        target = path

    connection = sqlite3.connect(
        target,
        timeout=BUSY_TIMEOUT_MS / 1000,
        uri=read_only,
    )
    try:
        configure_sqlite_connection(connection)
    except BaseException:
        connection.close()
        raise
    return connection


def create_sqlite_engine(database_path: str | Path | None = None) -> Engine:
    validate_sqlite_capability()
    path = resolve_database_path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(sqlite_url(path), connect_args={"timeout": BUSY_TIMEOUT_MS / 1000})
    event.listen(engine, "connect", _configure_connection)
    return engine
