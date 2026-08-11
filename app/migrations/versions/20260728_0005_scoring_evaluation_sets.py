"""Add immutable deterministic scoring evaluation evidence.

Revision ID: 20260728_0005
Revises: 20260728_0004
Create Date: 2026-07-28
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260728_0005"
down_revision: str | Sequence[str] | None = "20260728_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scoring_evaluation_sets",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("eligibility_evaluation_set_id", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("configuration_version", sa.Text(), nullable=False),
        sa.Column("input_hash", sa.Text(), nullable=False),
        sa.Column("input_json", sa.Text(), nullable=False),
        sa.Column("output_json", sa.Text(), nullable=False),
        sa.Column("candidate_count", sa.Integer(), nullable=False),
        sa.Column("eligible_count", sa.Integer(), nullable=False),
        sa.Column("ineligible_count", sa.Integer(), nullable=False),
        sa.Column("top_technician_id", sa.Text(), nullable=True),
        sa.Column("top_objective_score", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "schema_version = 'v1'",
            name="ck_scoring_schema_version",
        ),
        sa.CheckConstraint(
            "configuration_version = 'scoring-v1'",
            name="ck_scoring_configuration_version",
        ),
        sa.CheckConstraint(
            "length(input_hash) = 64 "
            "AND input_hash NOT GLOB '*[^0-9a-f]*'",
            name="ck_scoring_input_hash",
        ),
        sa.CheckConstraint("json_valid(input_json)", name="ck_scoring_input_json"),
        sa.CheckConstraint("json_valid(output_json)", name="ck_scoring_output_json"),
        sa.CheckConstraint(
            "candidate_count BETWEEN 0 AND 100",
            name="ck_scoring_candidate_count",
        ),
        sa.CheckConstraint(
            "eligible_count BETWEEN 0 AND candidate_count",
            name="ck_scoring_eligible_count",
        ),
        sa.CheckConstraint(
            "ineligible_count BETWEEN 0 AND candidate_count",
            name="ck_scoring_ineligible_count",
        ),
        sa.CheckConstraint(
            "eligible_count + ineligible_count = candidate_count",
            name="ck_scoring_partition_count",
        ),
        sa.CheckConstraint(
            "(eligible_count = 0 AND top_technician_id IS NULL "
            "AND top_objective_score IS NULL) OR "
            "(eligible_count > 0 AND top_technician_id IS NOT NULL "
            "AND top_objective_score IS NOT NULL)",
            name="ck_scoring_top_consistency",
        ),
        sa.CheckConstraint(
            "top_objective_score IS NULL OR "
            "(length(top_objective_score) BETWEEN 1 AND 80 "
            "AND top_objective_score NOT GLOB '*[^0-9.-]*')",
            name="ck_scoring_top_score_shape",
        ),
        sa.ForeignKeyConstraint(
            ["eligibility_evaluation_set_id"],
            ["eligibility_evaluation_sets.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["configuration_version"],
            ["configuration_versions.version"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "eligibility_evaluation_set_id",
            "configuration_version",
            "input_hash",
            name="uq_scoring_eligibility_configuration_input",
        ),
    )


def downgrade() -> None:
    op.drop_table("scoring_evaluation_sets")

