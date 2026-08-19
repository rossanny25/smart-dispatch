"""Add application users.

Revision ID: 20260818_0008
Revises: 20260728_0007
Create Date: 2026-08-18
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260818_0008"
down_revision: str | Sequence[str] | None = "20260728_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_users",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "role IN ('admin','tecnico','dispatcher')",
            name="ck_app_users_role",
        ),
        sa.CheckConstraint("is_active IN (0, 1)", name="ck_app_users_active"),
        sa.CheckConstraint(
            "length(username) BETWEEN 3 AND 80",
            name="ck_app_users_username",
        ),
        sa.CheckConstraint(
            "length(display_name) BETWEEN 1 AND 120",
            name="ck_app_users_name",
        ),
        sa.CheckConstraint(
            "password_hash LIKE 'pbkdf2_sha256$%'",
            name="ck_app_users_password_hash",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_app_users_username"),
    )


def downgrade() -> None:
    op.drop_table("app_users")
