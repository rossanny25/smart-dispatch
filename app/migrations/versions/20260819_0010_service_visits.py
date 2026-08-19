"""Add SQLite service visit calendar ledger."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260819_0010"
down_revision: str | None = "20260818_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "service_visits",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("order_id", sa.Text(), nullable=False),
        sa.Column(
            "technician_id",
            sa.Text(),
            sa.ForeignKey("service_technicians.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("technician_name", sa.Text(), nullable=False),
        sa.Column("client", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("zone", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("scheduled_start_at", sa.Text(), nullable=False),
        sa.Column("scheduled_end_at", sa.Text(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("feedback_comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "status IN ('programada','completada','cancelada')",
            name="ck_service_visits_status",
        ),
        sa.CheckConstraint(
            "duration_minutes BETWEEN 1 AND 1440",
            name="ck_service_visits_duration",
        ),
        sa.CheckConstraint(
            "length(order_id) BETWEEN 1 AND 120",
            name="ck_service_visits_order",
        ),
        sa.CheckConstraint(
            "length(technician_name) BETWEEN 2 AND 120",
            name="ck_service_visits_technician_name",
        ),
        sa.CheckConstraint(
            "length(zone) BETWEEN 2 AND 80",
            name="ck_service_visits_zone",
        ),
        sa.UniqueConstraint("order_id", name="uq_service_visits_order"),
    )
    op.create_index(
        "ix_service_visits_technician_start",
        "service_visits",
        ["technician_id", "scheduled_start_at"],
    )
    op.create_index(
        "ix_service_visits_start",
        "service_visits",
        ["scheduled_start_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_service_visits_start", table_name="service_visits")
    op.drop_index("ix_service_visits_technician_start", table_name="service_visits")
    op.drop_table("service_visits")
