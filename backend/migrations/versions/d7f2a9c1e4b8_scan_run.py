"""scan run

Revision ID: d7f2a9c1e4b8
Revises: c5e8a1f2b3d4
Create Date: 2026-11-22 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d7f2a9c1e4b8"
down_revision: str | None = "c5e8a1f2b3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scan_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trigger", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(length=20), nullable=True),
        sa.Column("components_scanned", sa.Integer(), nullable=True),
        sa.Column("findings_found", sa.Integer(), nullable=True),
        sa.Column("sources_with_errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("interrupted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scan_run_started_at", "scan_run", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_scan_run_started_at", table_name="scan_run")
    op.drop_table("scan_run")
