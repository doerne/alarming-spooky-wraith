"""inventory changed at

Revision ID: e3b8c5d2f6a1
Revises: d7f2a9c1e4b8
Create Date: 2026-11-22 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3b8c5d2f6a1"
down_revision: str | None = "d7f2a9c1e4b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "application", sa.Column("inventory_changed_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("application", "inventory_changed_at")
