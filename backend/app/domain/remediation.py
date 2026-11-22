"""Art der Erledigung und Fristen für offene Funde (reine Berechnung)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from app.domain.vulnerability import (
    Finding,
    FindingStatus,
    ResolutionSource,
    Severity,
    is_closed,
)

DEADLINE_DAYS: dict[Severity, int] = {
    Severity.KRITISCH: 7,
    Severity.HOCH: 30,
    Severity.MITTEL: 90,
    Severity.NIEDRIG: 180,
}
# Einführung der Fristen: Altfunde werden erst ab diesem Zeitpunkt gerechnet.
DEADLINE_START = datetime(2026, 11, 22, tzinfo=UTC)
DUE_SOON_DAYS = 7


class ClosureKind(StrEnum):
    """Wie ein Fund erledigt wurde."""

    FIXED_CONFIRMED = "fixed_confirmed"
    FIXED_REPORTED = "fixed_reported"
    FIXED_MANUAL = "fixed_manual"
    ACCEPTED = "accepted"
    FALSE_POSITIVE = "false_positive"


@dataclass(frozen=True)
class DeadlineSummary:
    overdue: int
    due_soon: int
    overdue_by_severity: dict[Severity, int]  # immer alle vier Stufen
    next_due_at: datetime | None


def _fixed_kind(source: ResolutionSource | None) -> ClosureKind:
    if source == ResolutionSource.SBOM:
        return ClosureKind.FIXED_CONFIRMED
    if source == ResolutionSource.REPORTED:
        return ClosureKind.FIXED_REPORTED
    return ClosureKind.FIXED_MANUAL


def closure_kind_of(finding: Finding) -> ClosureKind | None:
    """Art der Erledigung; ``None`` für offenen Bestand."""
    if finding.status == FindingStatus.FIXED:
        return _fixed_kind(finding.resolved_by)
    if finding.status == FindingStatus.ACCEPTED:
        return ClosureKind.ACCEPTED
    if finding.status == FindingStatus.FALSE_POSITIVE:
        return ClosureKind.FALSE_POSITIVE
    return None


def due_at(finding: Finding) -> datetime:
    """Fälligkeit: Frist der Stufe ab Erstsichtung, frühestens ab ``DEADLINE_START``."""
    start = DEADLINE_START
    if finding.first_seen_at is not None:
        start = max(finding.first_seen_at, DEADLINE_START)
    return start + timedelta(days=DEADLINE_DAYS[finding.risk.level])


def compute_deadlines(findings: Sequence[Finding], now: datetime) -> DeadlineSummary:
    """Überfällige und bald fällige Funde des offenen Bestands."""
    soon_limit = now + timedelta(days=DUE_SOON_DAYS)
    overdue_by_severity = {severity: 0 for severity in Severity}
    due_soon = 0
    upcoming: list[datetime] = []
    for finding in findings:
        if is_closed(finding.status):
            continue
        due = due_at(finding)
        if due <= now:
            overdue_by_severity[finding.risk.level] += 1
            continue
        upcoming.append(due)
        if due <= soon_limit:
            due_soon += 1
    return DeadlineSummary(
        overdue=sum(overdue_by_severity.values()),
        due_soon=due_soon,
        overdue_by_severity=overdue_by_severity,
        next_due_at=min(upcoming, default=None),
    )
