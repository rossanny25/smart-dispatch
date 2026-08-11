"""Add immutable recommendation confidence evidence.

Revision ID: 20260728_0006
Revises: 20260728_0005
Create Date: 2026-07-28
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260728_0006"
down_revision: str | Sequence[str] | None = "20260728_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "confidence_evaluation_sets",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("scoring_evaluation_set_id", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("configuration_version", sa.Text(), nullable=False),
        sa.Column("input_hash", sa.Text(), nullable=False),
        sa.Column("input_json", sa.Text(), nullable=False),
        sa.Column("output_json", sa.Text(), nullable=False),
        sa.Column("eligible_count", sa.Integer(), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("recommended_technician_id", sa.Text(), nullable=True),
        sa.Column("confidence_value", sa.Text(), nullable=True),
        sa.Column("confidence_label", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "schema_version = 'v1'", name="ck_confidence_schema_version"
        ),
        sa.CheckConstraint(
            "configuration_version = 'confidence-v1'",
            name="ck_confidence_configuration_version",
        ),
        sa.CheckConstraint(
            "length(input_hash) = 64 "
            "AND input_hash NOT GLOB '*[^0-9a-f]*'",
            name="ck_confidence_input_hash",
        ),
        sa.CheckConstraint(
            "json_valid(input_json)", name="ck_confidence_input_json"
        ),
        sa.CheckConstraint(
            "json_valid(output_json)", name="ck_confidence_output_json"
        ),
        sa.CheckConstraint(
            "eligible_count BETWEEN 0 AND 100",
            name="ck_confidence_eligible_count",
        ),
        sa.CheckConstraint(
            "source_count BETWEEN 0 AND 103",
            name="ck_confidence_source_count",
        ),
        sa.CheckConstraint(
            "warning_count BETWEEN 0 AND source_count",
            name="ck_confidence_warning_count",
        ),
        sa.CheckConstraint(
            "(eligible_count = 0 AND recommended_technician_id IS NULL "
            "AND confidence_value IS NULL AND confidence_label IS NULL) OR "
            "(eligible_count > 0 AND recommended_technician_id IS NOT NULL "
            "AND confidence_value IS NOT NULL "
            "AND confidence_label IN ('low','medium','high'))",
            name="ck_confidence_summary_consistency",
        ),
        sa.ForeignKeyConstraint(
            ["scoring_evaluation_set_id"],
            ["scoring_evaluation_sets.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["configuration_version"],
            ["configuration_versions.version"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scoring_evaluation_set_id",
            "configuration_version",
            "input_hash",
            name="uq_confidence_scoring_configuration_input",
        ),
    )


def downgrade() -> None:
    op.drop_table("confidence_evaluation_sets")
