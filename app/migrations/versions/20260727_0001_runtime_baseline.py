"""Establish the migration baseline without premature domain tables.

Revision ID: 20260727_0001
Revises:
Create Date: 2026-07-27
"""

from typing import Sequence


revision: str = "20260727_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
