"""Add service technicians.

Revision ID: 20260818_0009
Revises: 20260818_0008
Create Date: 2026-08-18
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260818_0009"
down_revision: str | Sequence[str] | None = "20260818_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "service_technicians",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("zone", sa.Text(), nullable=False),
        sa.Column("certifications_json", sa.Text(), nullable=False),
        sa.Column("shift_start", sa.Text(), nullable=False),
        sa.Column("shift_end", sa.Text(), nullable=False),
        sa.Column("active_workload_hours", sa.Float(), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("ppe_json", sa.Text(), nullable=False),
        sa.Column("gps_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "status IN ('disponible','ocupado','fuera_servicio')",
            name="ck_service_technicians_status",
        ),
        sa.CheckConstraint(
            "length(name) BETWEEN 2 AND 120",
            name="ck_service_technicians_name",
        ),
        sa.CheckConstraint(
            "length(zone) BETWEEN 2 AND 80",
            name="ck_service_technicians_zone",
        ),
        sa.CheckConstraint(
            "active_workload_hours BETWEEN 0 AND 16",
            name="ck_service_technicians_workload",
        ),
        sa.CheckConstraint(
            "rating BETWEEN 0 AND 5",
            name="ck_service_technicians_rating",
        ),
        sa.CheckConstraint(
            "shift_start GLOB '[0-2][0-9]:[0-5][0-9]' "
            "AND substr(shift_start, 1, 2) < '24'",
            name="ck_service_technicians_shift_start",
        ),
        sa.CheckConstraint(
            "shift_end GLOB '[0-2][0-9]:[0-5][0-9]' "
            "AND substr(shift_end, 1, 2) < '24'",
            name="ck_service_technicians_shift_end",
        ),
        sa.CheckConstraint(
            "json_valid(certifications_json) "
            "AND json_type(certifications_json) = 'array'",
            name="ck_service_technicians_certifications",
        ),
        sa.CheckConstraint(
            "json_valid(ppe_json) AND json_type(ppe_json) = 'array'",
            name="ck_service_technicians_ppe",
        ),
        sa.CheckConstraint(
            "json_valid(gps_json)",
            name="ck_service_technicians_gps",
        ),
        sa.CheckConstraint(
            "json_type(gps_json) = 'object' "
            "AND json_type(gps_json, '$.lat') IN ('integer','real') "
            "AND json_type(gps_json, '$.lng') IN ('integer','real')",
            name="ck_service_technicians_gps_shape",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_service_technicians_name"),
    )


def downgrade() -> None:
    op.drop_table("service_technicians")
