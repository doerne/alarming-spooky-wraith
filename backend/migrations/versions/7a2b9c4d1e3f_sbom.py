"""sbom

Revision ID: 7a2b9c4d1e3f
Revises: 3c1d2e4f5a6b
Create Date: 2026-11-21 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7a2b9c4d1e3f"
down_revision: str | None = "3c1d2e4f5a6b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sbom",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["application.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_id", "name", name="uq_sbom_application_name"),
    )
    op.create_table(
        "sbom_version",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sbom_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("serial_number", sa.String(length=100), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("components", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["sbom_id"], ["sbom.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("component", sa.Column("sbom_id", sa.Integer(), nullable=True))
    op.add_column(
        "component",
        sa.Column("checked", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_foreign_key("fk_component_sbom", "component", "sbom", ["sbom_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_component_sbom", "component", type_="foreignkey")
    op.drop_column("component", "checked")
    op.drop_column("component", "sbom_id")
    op.drop_table("sbom_version")
    op.drop_table("sbom")
