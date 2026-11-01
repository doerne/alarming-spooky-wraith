"""source setting

Revision ID: 3c1d2e4f5a6b
Revises: eb5f579d64ab
Create Date: 2026-11-01 15:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "3c1d2e4f5a6b"
down_revision: str | None = "eb5f579d64ab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_setting",
        sa.Column("source_key", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("api_key", sa.Text(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(length=20), nullable=True),
        sa.Column("last_message", sa.Text(), nullable=False),
        sa.Column("last_findings", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("source_key"),
    )


def downgrade() -> None:
    op.drop_table("source_setting")
