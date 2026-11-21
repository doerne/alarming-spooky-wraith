"""github integration fields

Revision ID: c5e8a1f2b3d4
Revises: ad5e2f7a4b6c
Create Date: 2026-11-21 19:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c5e8a1f2b3d4"
down_revision: str | None = "ad5e2f7a4b6c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("application", sa.Column("github_repository", sa.String(length=140), nullable=True))
    op.add_column("application", sa.Column("auto_issue_min_level", sa.String(length=20), nullable=True))
    op.add_column(
        "application", sa.Column("auto_issue_enabled_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("application", sa.Column("github_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "application",
        sa.Column("github_sync_message", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column("finding", sa.Column("issue_state", sa.String(length=10), nullable=True))
    op.add_column("finding", sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("finding", "first_seen_at")
    op.drop_column("finding", "issue_state")
    op.drop_column("application", "github_sync_message")
    op.drop_column("application", "github_synced_at")
    op.drop_column("application", "auto_issue_enabled_at")
    op.drop_column("application", "auto_issue_min_level")
    op.drop_column("application", "github_repository")
