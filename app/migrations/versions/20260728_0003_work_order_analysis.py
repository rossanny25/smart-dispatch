"""Add immutable Analyze configuration and Work Order analysis evidence.

Revision ID: 20260728_0003
Revises: 20260728_0002
Create Date: 2026-07-28
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260728_0003"
down_revision: str | Sequence[str] | None = "20260728_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "configuration_versions",
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("contract_version", sa.Text(), nullable=False),
        sa.Column("registry_json", sa.Text(), nullable=False),
        sa.Column("registry_sha256", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "contract_version = 'v1'",
            name="ck_configuration_contract_version",
        ),
        sa.CheckConstraint(
            "json_valid(registry_json)",
            name="ck_configuration_registry_json",
        ),
        sa.CheckConstraint(
            "length(registry_sha256) = 64 "
            "AND registry_sha256 NOT GLOB '*[^0-9a-f]*'",
            name="ck_configuration_registry_sha256",
        ),
        sa.PrimaryKeyConstraint("version"),
    )
    op.create_table(
        "work_order_analyses",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("work_order_id", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("configuration_version", sa.Text(), nullable=False),
        sa.Column("input_hash", sa.Text(), nullable=False),
        sa.Column("output_json", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("sla_target_minutes", sa.Integer(), nullable=False),
        sa.Column("required_certifications_json", sa.Text(), nullable=False),
        sa.Column("estimated_service_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "schema_version = 'v1'",
            name="ck_analysis_schema_version",
        ),
        sa.CheckConstraint(
            "configuration_version = 'analysis-v1'",
            name="ck_analysis_configuration_version",
        ),
        sa.CheckConstraint(
            "category IN ('gas','electricity','telecommunications',"
            "'plumbing','hvac','maintenance')",
            name="ck_analysis_category",
        ),
        sa.CheckConstraint(
            "length(input_hash) = 64 "
            "AND input_hash NOT GLOB '*[^0-9a-f]*'",
            name="ck_analysis_input_hash",
        ),
        sa.CheckConstraint(
            "json_valid(output_json)",
            name="ck_analysis_output_json",
        ),
        sa.CheckConstraint(
            "json_valid(required_certifications_json)",
            name="ck_analysis_certifications_json",
        ),
        sa.CheckConstraint("priority BETWEEN 1 AND 5", name="ck_analysis_priority"),
        sa.CheckConstraint(
            "sla_target_minutes BETWEEN 1 AND 10080",
            name="ck_analysis_sla_minutes",
        ),
        sa.CheckConstraint(
            "estimated_service_duration_minutes BETWEEN 15 AND 1440",
            name="ck_analysis_duration_minutes",
        ),
        sa.ForeignKeyConstraint(
            ["configuration_version"],
            ["configuration_versions.version"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["work_order_id"],
            ["work_orders.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "work_order_id",
            "configuration_version",
            name="uq_work_order_analysis_configuration",
        ),
    )


def downgrade() -> None:
    op.drop_table("work_order_analyses")
    op.drop_table("configuration_versions")
