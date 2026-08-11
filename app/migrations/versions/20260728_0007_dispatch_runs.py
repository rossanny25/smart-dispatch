"""Add auditable dispatch-run evidence.

Revision ID: 20260728_0007
Revises: 20260728_0006
Create Date: 2026-07-28
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260728_0007"
down_revision: str | Sequence[str] | None = "20260728_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dispatch_runs",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("work_order_id", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("configuration_version", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("snapshot_sha256", sa.Text(), nullable=False),
        sa.Column("resource_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.CheckConstraint("schema_version = 'v1'"),
        sa.CheckConstraint("configuration_version = 'dispatch-v1'"),
        sa.CheckConstraint(
            "state IN ('CAPTURE','ANALYZE','PLAN','EVALUATE',"
            "'WAIT_FOR_DECISION','NO_FEASIBLE_CANDIDATES','FAILED')"
        ),
        sa.CheckConstraint("revision BETWEEN 0 AND 4"),
        sa.CheckConstraint("json_valid(snapshot_json)"),
        sa.CheckConstraint("json_valid(resource_json)"),
        sa.CheckConstraint(
            "length(snapshot_sha256) = 64 "
            "AND snapshot_sha256 NOT GLOB '*[^0-9a-f]*'"
        ),
        sa.ForeignKeyConstraint(
            ["work_order_id"], ["work_orders.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["configuration_version"],
            ["configuration_versions.version"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "run_snapshots",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("stage", sa.Text(), nullable=True),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.CheckConstraint("kind IN ('run_input','stage_output')"),
        sa.CheckConstraint("json_valid(content_json)"),
        sa.CheckConstraint(
            "length(content_sha256) = 64 "
            "AND content_sha256 NOT GLOB '*[^0-9a-f]*'"
        ),
        sa.ForeignKeyConstraint(["run_id"], ["dispatch_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "run_id"),
        sa.UniqueConstraint("run_id", "kind", "stage"),
    )
    op.create_index(
        "uq_run_input_snapshot",
        "run_snapshots",
        ["run_id"],
        unique=True,
        sqlite_where=sa.text("kind = 'run_input'"),
    )
    op.create_table(
        "stage_executions",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("configuration_version", sa.Text(), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.Text(), nullable=False),
        sa.Column("ended_at", sa.Text(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("input_ref", sa.Text(), nullable=False),
        sa.Column("run_snapshot_ref", sa.Text(), nullable=False),
        sa.Column("output_ref", sa.Text(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_type", sa.Text(), nullable=True),
        sa.Column("safe_message", sa.Text(), nullable=True),
        sa.CheckConstraint("sequence BETWEEN 1 AND 4"),
        sa.CheckConstraint(
            "(sequence = 1 AND stage = 'CAPTURE') OR "
            "(sequence = 2 AND stage = 'ANALYZE') OR "
            "(sequence = 3 AND stage = 'PLAN') OR "
            "(sequence = 4 AND stage = 'EVALUATE')"
        ),
        sa.CheckConstraint("schema_version = 'v1'"),
        sa.CheckConstraint("configuration_version = 'dispatch-v1'"),
        sa.CheckConstraint("duration_ms >= 0"),
        sa.CheckConstraint("ended_at >= started_at"),
        sa.CheckConstraint("attempt = 1"),
        sa.CheckConstraint("status IN ('completed','failed')"),
        sa.CheckConstraint(
            "(status = 'completed' AND output_ref IS NOT NULL "
            "AND error_code IS NULL AND error_type IS NULL "
            "AND safe_message IS NULL) OR "
            "(status = 'failed' AND output_ref IS NULL "
            "AND error_code IS NOT NULL AND error_type = 'STAGE_FAILURE' "
            "AND safe_message IS NOT NULL)"
        ),
        sa.ForeignKeyConstraint(
            ["input_ref", "run_id"],
            ["run_snapshots.id", "run_snapshots.run_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["run_snapshot_ref", "run_id"],
            ["run_snapshots.id", "run_snapshots.run_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["output_ref", "run_id"],
            ["run_snapshots.id", "run_snapshots.run_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["run_id"], ["dispatch_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "sequence"),
    )
    op.create_table(
        "state_transitions",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("from_state", sa.Text(), nullable=True),
        sa.Column("to_state", sa.Text(), nullable=False),
        sa.Column("outcome_code", sa.Text(), nullable=False),
        sa.Column("run_revision", sa.Integer(), nullable=False),
        sa.Column("configuration_version", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.Text(), nullable=False),
        sa.CheckConstraint("sequence BETWEEN 0 AND 4"),
        sa.CheckConstraint("run_revision = sequence"),
        sa.CheckConstraint("configuration_version = 'dispatch-v1'"),
        sa.CheckConstraint(
            "(from_state IS NULL AND to_state = 'CAPTURE') OR "
            "(from_state = 'CAPTURE' AND to_state IN ('ANALYZE','FAILED')) OR "
            "(from_state = 'ANALYZE' AND to_state IN ('PLAN','FAILED')) OR "
            "(from_state = 'PLAN' AND to_state IN ('EVALUATE','FAILED')) OR "
            "(from_state = 'EVALUATE' AND to_state IN "
            "('WAIT_FOR_DECISION','NO_FEASIBLE_CANDIDATES','FAILED'))"
        ),
        sa.ForeignKeyConstraint(["run_id"], ["dispatch_runs.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "sequence"),
    )
def downgrade() -> None:
    op.drop_table("state_transitions")
    op.drop_table("stage_executions")
    op.drop_table("run_snapshots")
    op.drop_table("dispatch_runs")
