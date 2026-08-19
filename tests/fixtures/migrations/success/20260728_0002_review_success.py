"""Test-only revision proving backup-before-successful-upgrade behavior."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260728_test_success"
down_revision: str | Sequence[str] | None = "20260818_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_migration_marker",
        sa.Column("value", sa.String(), nullable=False),
    )
    op.execute(
        sa.text("INSERT INTO review_migration_marker (value) VALUES ('migrated')")
    )


def downgrade() -> None:
    op.drop_table("review_migration_marker")
