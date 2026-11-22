"""Art der Erledigung und Fristen für offene Funde (reine Berechnung)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from app.domain.ports import VersionComparator
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
UPDATE_TARGET_LIMIT = 5


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


@dataclass(frozen=True)
class OpenItem:
    """Ein offener Fund mit den Angaben, die für Update-Ziele nötig sind."""

    package_name: str
    ecosystem: str | None
    found_version: str
    fixed_version: str | None
    application_id: int


@dataclass(frozen=True)
class UpdateTarget:
    package_name: str
    ecosystem: str | None
    target_version: str
    findings: int
    applications: int


@dataclass(frozen=True)
class UpdateSummary:
    targets: list[UpdateTarget]
    fixable_open: int
    open_total: int
    more_packages: int


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


def _valid_fix(item: OpenItem, versions: VersionComparator) -> str | None:
    if item.fixed_version is None:
        return None
    if versions.is_newer(item.ecosystem, item.fixed_version, item.found_version):
        return item.fixed_version
    return None


def _highest(ecosystem: str | None, fixes: Sequence[str], versions: VersionComparator) -> str:
    highest = fixes[0]
    for fix in fixes[1:]:
        if versions.is_newer(ecosystem, fix, highest):
            highest = fix
    return highest


def compute_update_targets(
    items: Sequence[OpenItem],
    versions: VersionComparator,
    limit: int = UPDATE_TARGET_LIMIT,
) -> UpdateSummary:
    """Pakete mit den meisten behebbaren offenen Funden samt Zielversion."""
    groups: dict[tuple[str | None, str], list[tuple[OpenItem, str]]] = {}
    for item in items:
        fix = _valid_fix(item, versions)
        if fix is not None:
            groups.setdefault((item.ecosystem, item.package_name), []).append((item, fix))
    targets = [
        UpdateTarget(
            package_name=name,
            ecosystem=ecosystem,
            target_version=_highest(ecosystem, [fix for _, fix in entries], versions),
            findings=len(entries),
            applications=len({entry.application_id for entry, _ in entries}),
        )
        for (ecosystem, name), entries in groups.items()
    ]
    targets.sort(key=lambda target: (-target.findings, target.package_name, target.ecosystem or ""))
    return UpdateSummary(
        targets=targets[:limit],
        fixable_open=sum(target.findings for target in targets),
        open_total=len(items),
        more_packages=max(0, len(targets) - limit),
    )
