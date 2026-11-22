"""retired components and resolved findings

Revision ID: 9c4d1e6f3a5b
Revises: 8b3c0d5e2f4a
Create Date: 2026-11-21 16:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9c4d1e6f3a5b"
down_revision: str | None = "8b3c0d5e2f4a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("component", sa.Column("retired_in_version_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_component_retired_version", "component", "sbom_version", ["retired_in_version_id"], ["id"]
    )
    op.add_column("finding", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("finding", sa.Column("resolution", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("finding", "resolution")
    op.drop_column("finding", "resolved_at")
    op.drop_constraint("fk_component_retired_version", "component", type_="foreignkey")
    op.drop_column("component", "retired_in_version_id")
