"""advisory alias

Revision ID: 8b3c0d5e2f4a
Revises: 7a2b9c4d1e3f
Create Date: 2026-11-21 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8b3c0d5e2f4a"
down_revision: str | None = "7a2b9c4d1e3f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "advisory_alias",
        sa.Column("alias_id", sa.String(length=64), nullable=False),
        sa.Column("advisory_id", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("alias_id"),
    )


def downgrade() -> None:
    op.drop_table("advisory_alias")
