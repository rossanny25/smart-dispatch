"""Test-only revision that mutates SQLite before failing."""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260728_test_failure"
down_revision: str | Sequence[str] | None = "20260819_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_partial_marker",
        sa.Column("value", sa.String(), nullable=False),
    )
    op.execute(sa.text("UPDATE sentinel SET value = 'partially changed'"))
    raise RuntimeError("revision 20260728_test_failure")


def downgrade() -> None:
    op.drop_table("review_partial_marker")
