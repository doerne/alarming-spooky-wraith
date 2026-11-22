"""finding closed at

Revision ID: f4c9d3e7a2b1
Revises: e3b8c5d2f6a1
Create Date: 2026-11-22 16:00:00.000000
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from alembic import op

revision: str = "f4c9d3e7a2b1"
down_revision: str | None = "e3b8c5d2f6a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BASELINE_WEEKS = 53


def upgrade() -> None:
    op.add_column("finding", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    # Altbestand bekommt einen Zeitpunkt vor jedem Diagrammzeitraum (max. 52 Wochen),
    # damit er als Ausgangsbestand und nie als „neu“ gezählt wird.
    baseline = datetime.now(UTC) - timedelta(weeks=BASELINE_WEEKS)
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE finding SET first_seen_at = :baseline WHERE first_seen_at IS NULL"),
        {"baseline": baseline},
    )
    connection.execute(
        sa.text(
            "UPDATE finding SET closed_at = resolved_at "
            "WHERE status = 'behoben' AND resolved_at IS NOT NULL"
        )
    )
    # Funde mit echtem first_seen_at, die vor der Migration akzeptiert/false_positive waren,
    # erhalten closed_at = BASELINE < first_seen_at. _is_trackable schließt sie deshalb aus dem
    # Verlauf aus (einmaliger, bewusster Effekt; der Bestand bleibt korrekt).
    connection.execute(
        sa.text(
            "UPDATE finding SET closed_at = :baseline "
            "WHERE status IN ('behoben', 'akzeptiert', 'false_positive') AND closed_at IS NULL"
        ),
        {"baseline": baseline},
    )


def downgrade() -> None:
    # Die nachgetragenen first_seen_at-Werte bleiben bewusst erhalten.
    op.drop_column("finding", "closed_at")
