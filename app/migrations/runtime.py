"""Programmatic Alembic operations for fail-closed startup."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory

from app.adapters.persistence.database import (
    PROJECT_ROOT,
    create_sqlite_engine,
    sqlite_url,
)


MIGRATIONS_ROOT = Path(__file__).resolve().parent
ALEMBIC_INI_PATH = PROJECT_ROOT / "alembic.ini"


def build_alembic_config(database_path: str | Path | None = None) -> Config:
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(MIGRATIONS_ROOT))
    rendered_url = sqlite_url(database_path).render_as_string(hide_password=False)
    config.set_main_option(
        "sqlalchemy.url",
        rendered_url.replace("%", "%%"),
    )
    return config


def get_head_revision() -> str:
    script = ScriptDirectory.from_config(build_alembic_config())
    head = script.get_current_head()
    if head is None:
        raise RuntimeError("Alembic migration head is not configured.")
    return head


def get_current_revision(database_path: str | Path | None = None) -> str | None:
    engine = create_sqlite_engine(database_path)
    try:
        with engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()


def has_pending_migrations(database_path: str | Path | None = None) -> bool:
    return get_current_revision(database_path) != get_head_revision()


def upgrade_to_head(database_path: str | Path | None = None) -> None:
    engine = create_sqlite_engine(database_path)
    config = build_alembic_config(database_path)
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
    finally:
        engine.dispose()
