"""Expand operational admin data for technicians, orders, and visits."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260819_0011"
down_revision: str | None = "20260819_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "service_technicians",
        sa.Column("contact_phone", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "service_technicians",
        sa.Column("contact_email", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "service_technicians",
        sa.Column("documents_json", sa.Text(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "service_technicians",
        sa.Column("audit_log_json", sa.Text(), nullable=False, server_default="[]"),
    )

    op.create_table(
        "service_orders",
        sa.Column("id", sa.Text(), primary_key=True, nullable=False),
        sa.Column("client", sa.Text(), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("zone", sa.Text(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("structured_data_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pendiente','completada','cancelada')",
            name="ck_service_orders_status",
        ),
        sa.CheckConstraint("length(id) BETWEEN 1 AND 120", name="ck_service_orders_id"),
        sa.CheckConstraint("length(client) BETWEEN 1 AND 160", name="ck_service_orders_client"),
        sa.CheckConstraint("length(zone) BETWEEN 2 AND 80", name="ck_service_orders_zone"),
        sa.CheckConstraint("json_valid(structured_data_json)", name="ck_service_orders_structured"),
    )
    op.create_index(
        "ix_service_orders_status_zone",
        "service_orders",
        ["status", "zone"],
    )

    with op.batch_alter_table("service_visits") as batch_op:
        batch_op.drop_constraint("ck_service_visits_status", type_="check")
        batch_op.create_check_constraint(
            "ck_service_visits_status",
            "status IN ('programada','en_curso','completada','cancelada')",
        )


def downgrade() -> None:
    with op.batch_alter_table("service_visits") as batch_op:
        batch_op.drop_constraint("ck_service_visits_status", type_="check")
        batch_op.create_check_constraint(
            "ck_service_visits_status",
            "status IN ('programada','completada','cancelada')",
        )

    op.drop_index("ix_service_orders_status_zone", table_name="service_orders")
    op.drop_table("service_orders")

    op.drop_column("service_technicians", "audit_log_json")
    op.drop_column("service_technicians", "documents_json")
    op.drop_column("service_technicians", "contact_email")
    op.drop_column("service_technicians", "contact_phone")
