"""finding report fields

Revision ID: ad5e2f7a4b6c
Revises: 9c4d1e6f3a5b
Create Date: 2026-11-21 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "ad5e2f7a4b6c"
down_revision: str | None = "9c4d1e6f3a5b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("finding", sa.Column("resolved_by", sa.String(length=20), nullable=True))
    op.add_column("finding", sa.Column("issue_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("finding", "issue_url")
    op.drop_column("finding", "resolved_by")
