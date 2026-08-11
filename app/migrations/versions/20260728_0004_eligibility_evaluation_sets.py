"""Add immutable pre-scoring eligibility evaluation evidence.

Revision ID: 20260728_0004
Revises: 20260728_0003
Create Date: 2026-07-28
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260728_0004"
down_revision: str | Sequence[str] | None = "20260728_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_analysis_id_work_order",
        "work_order_analyses",
        ["id", "work_order_id"],
        unique=True,
    )
    op.create_table(
        "eligibility_evaluation_sets",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("work_order_id", sa.Text(), nullable=False),
        sa.Column("work_order_analysis_id", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("configuration_version", sa.Text(), nullable=False),
        sa.Column("input_hash", sa.Text(), nullable=False),
        sa.Column("input_json", sa.Text(), nullable=False),
        sa.Column("output_json", sa.Text(), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("eligible_count", sa.Integer(), nullable=False),
        sa.Column("ineligible_count", sa.Integer(), nullable=False),
        sa.Column("no_feasible_candidates", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "schema_version = 'v1'",
            name="ck_eligibility_schema_version",
        ),
        sa.CheckConstraint(
            "configuration_version = 'eligibility-v1'",
            name="ck_eligibility_configuration_version",
        ),
        sa.CheckConstraint(
            "length(input_hash) = 64 "
            "AND input_hash NOT GLOB '*[^0-9a-f]*'",
            name="ck_eligibility_input_hash",
        ),
        sa.CheckConstraint(
            "json_valid(input_json)",
            name="ck_eligibility_input_json",
        ),
        sa.CheckConstraint(
            "json_valid(output_json)",
            name="ck_eligibility_output_json",
        ),
        sa.CheckConstraint(
            "candidate_count BETWEEN 0 AND 100",
            name="ck_eligibility_candidate_count",
        ),
        sa.CheckConstraint(
            "eligible_count BETWEEN 0 AND candidate_count",
            name="ck_eligibility_eligible_count",
        ),
        sa.CheckConstraint(
            "ineligible_count BETWEEN 0 AND candidate_count",
            name="ck_eligibility_ineligible_count",
        ),
        sa.CheckConstraint(
            "eligible_count + ineligible_count = candidate_count",
            name="ck_eligibility_partition_count",
        ),
        sa.CheckConstraint(
            "no_feasible_candidates IN (0, 1)",
            name="ck_eligibility_no_feasible_boolean",
        ),
        sa.CheckConstraint(
            "(no_feasible_candidates = 1 AND eligible_count = 0) "
            "OR (no_feasible_candidates = 0 AND eligible_count > 0)",
            name="ck_eligibility_no_feasible_consistency",
        ),
        sa.ForeignKeyConstraint(
            ["work_order_id"],
            ["work_orders.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["work_order_analysis_id", "work_order_id"],
            ["work_order_analyses.id", "work_order_analyses.work_order_id"],
            ondelete="RESTRICT",
            name="fk_eligibility_analysis_work_order",
        ),
        sa.ForeignKeyConstraint(
            ["configuration_version"],
            ["configuration_versions.version"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "work_order_analysis_id",
            "configuration_version",
            "input_hash",
            name="uq_eligibility_analysis_configuration_input",
        ),
    )


def downgrade() -> None:
    op.drop_table("eligibility_evaluation_sets")
    op.drop_index(
        "uq_analysis_id_work_order",
        table_name="work_order_analyses",
    )
