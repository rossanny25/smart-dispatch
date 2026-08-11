"""Verified SQLite online backup and restore operations."""

from datetime import UTC, datetime
from pathlib import Path
import sqlite3
from uuid import uuid4

from app.adapters.persistence.database import PROJECT_ROOT, connect_sqlite


DEFAULT_BACKUP_DIR = PROJECT_ROOT / "data" / "backups"


class BackupError(RuntimeError):
    """A backup could not be created or verified safely."""


def verify_database_integrity(database_path: str | Path) -> bool:
    path = Path(database_path)
    try:
        with connect_sqlite(path, read_only=True) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()
    except (sqlite3.Error, RuntimeError):
        return False
    return result == ("ok",)


def create_verified_backup(
    database_path: str | Path,
    backup_dir: str | Path | None = None,
) -> Path:
    source_path = Path(database_path)
    destination_dir = Path(backup_dir) if backup_dir else DEFAULT_BACKUP_DIR
    destination_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    destination_path = (
        destination_dir
        / f"{source_path.stem}-{timestamp}-{uuid4().hex[:8]}.backup.db"
    )

    try:
        with connect_sqlite(source_path) as source, connect_sqlite(
            destination_path
        ) as destination:
            source.backup(destination)
    except (sqlite3.Error, RuntimeError) as error:
        raise BackupError("SQLite backup could not be completed.") from error

    if not verify_database_integrity(destination_path):
        raise BackupError("SQLite backup failed its integrity check.")
    return destination_path


def restore_verified_backup(
    backup_path: str | Path,
    database_path: str | Path,
) -> None:
    source_path = Path(backup_path)
    destination_path = Path(database_path)
    if not verify_database_integrity(source_path):
        raise BackupError("Refusing to restore an invalid SQLite backup.")

    try:
        with connect_sqlite(source_path, read_only=True) as source, connect_sqlite(
            destination_path
        ) as destination:
            source.backup(destination)
    except (sqlite3.Error, RuntimeError) as error:
        raise BackupError("SQLite backup restore could not be completed.") from error

    if not verify_database_integrity(destination_path):
        raise BackupError("Restored SQLite database failed its integrity check.")
