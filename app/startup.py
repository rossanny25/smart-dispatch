"""Fail-closed startup orchestration for SQLite and Alembic."""

from collections.abc import Callable
from contextlib import contextmanager
import fcntl
from pathlib import Path
from typing import Iterator

from app.auth import ensure_default_admin_user
from app.adapters.legacy.compatibility import (
    bootstrap_service_orders,
    bootstrap_service_technicians,
)
from app.adapters.persistence.backup import (
    create_verified_backup,
    restore_verified_backup,
)
from app.adapters.persistence.database import (
    resolve_database_path,
    validate_sqlite_capability,
)
from app.migrations.runtime import has_pending_migrations, upgrade_to_head


class StartupError(RuntimeError):
    """A sanitized startup failure that must prevent HTTP serving."""


PendingChecker = Callable[[Path], bool]
MigrationRunner = Callable[[Path], None]
BackupCreator = Callable[[Path, str | Path | None], Path]
BackupRestorer = Callable[[Path, Path], None]


@contextmanager
def _startup_lock(database_path: Path) -> Iterator[None]:
    """Serialize migration preparation for every process targeting one database."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = Path(f"{database_path}.startup.lock")
    with lock_path.open("a+b") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _remove_fresh_database_artifacts(database_path: Path) -> None:
    """Remove only files created by a failed first startup."""
    for suffix in ("", "-wal", "-shm", "-journal"):
        Path(f"{database_path}{suffix}").unlink(missing_ok=True)


def prepare_runtime(
    database_path: str | Path | None = None,
    backup_dir: str | Path | None = None,
    *,
    pending_checker: PendingChecker = has_pending_migrations,
    migration_runner: MigrationRunner = upgrade_to_head,
    backup_creator: BackupCreator = create_verified_backup,
    backup_restorer: BackupRestorer = restore_verified_backup,
) -> None:
    path = resolve_database_path(database_path)
    try:
        with _startup_lock(path):
            existed_before = path.exists()
            backup_path: Path | None = None
            operation = "SQLite capability validation"
            try:
                validate_sqlite_capability()
                operation = "Alembic pending-revision detection"
                pending = pending_checker(path)
                if pending and existed_before:
                    operation = "pre-upgrade SQLite backup"
                    backup_path = backup_creator(path, backup_dir)
                if pending:
                    operation = "Alembic upgrade to head"
                    migration_runner(path)
                operation = "Alembic head verification"
                if pending_checker(path):
                    raise RuntimeError("migration head was not reached")
                operation = "default admin bootstrap"
                ensure_default_admin_user(path)
                operation = "service technician bootstrap"
                bootstrap_service_technicians(path)
                operation = "service order bootstrap"
                bootstrap_service_orders(path)
            except BaseException as error:
                recovery_operation = "verified backup restoration"
                try:
                    if backup_path is not None:
                        backup_restorer(backup_path, path)
                    elif not existed_before:
                        recovery_operation = "failed fresh-database cleanup"
                        _remove_fresh_database_artifacts(path)
                except BaseException as recovery_error:
                    raise StartupError(
                        f"{operation} failed and {recovery_operation} failed; "
                        "HTTP server was not started"
                    ) from recovery_error

                if not isinstance(error, Exception):
                    raise
                raise StartupError(
                    f"{operation} failed; recovery completed; "
                    "HTTP server was not started"
                ) from error
    except StartupError:
        raise
    except Exception as error:
        raise StartupError(
            "startup serialization failed; HTTP server was not started"
        ) from error
