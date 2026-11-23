"""Regeln der Inventar-Übersicht: Scan-Zustand und SBOM-Alter je Anwendung."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.domain.vulnerability import Finding, Severity, is_closed

# Eine SBOM, die einen Monat nicht erneuert wurde, deutet auf eine fehlende Pipeline hin.
SBOM_STALE_AFTER_DAYS = 30


class ScanState(StrEnum):
    """Ob der letzte verwertbare Scan das aktuelle Inventar einer Anwendung gesehen hat."""

    CURRENT = "current"
    CHANGED_SINCE_SCAN = "changed_since_scan"
    NEVER_SCANNED = "never_scanned"


def scan_state(
    inventory_changed_at: datetime | None, last_usable_scan_started_at: datetime | None
) -> ScanState:
    """Geändert heißt: echt nach Beginn des letzten verwertbaren Laufs (Gleichstand zählt nicht)."""
    if last_usable_scan_started_at is None:
        return ScanState.NEVER_SCANNED
    if inventory_changed_at is not None and inventory_changed_at > last_usable_scan_started_at:
        return ScanState.CHANGED_SINCE_SCAN
    return ScanState.CURRENT


def is_sbom_stale(latest_upload_at: datetime | None, now: datetime) -> bool:
    """Ohne SBOM oder mit einer älter als ``SBOM_STALE_AFTER_DAYS`` gilt sie als veraltet."""
    if latest_upload_at is None:
        return True
    return now - latest_upload_at > timedelta(days=SBOM_STALE_AFTER_DAYS)


def count_open_by_severity(findings: Iterable[Finding]) -> dict[Severity, int]:
    """Offene Funde je Stufe; alle vier Stufen sind immer enthalten."""
    counts = dict.fromkeys(Severity, 0)
    for finding in findings:
        if not is_closed(finding.status):
            counts[finding.risk.level] += 1
    return counts


@dataclass(frozen=True)
class ApplicationOverview:
    application_id: int
    name: str
    description: str
    open_by_severity: dict[Severity, int]  # aus count_open_by_severity
    overdue: int
    component_count: int
    latest_sbom_upload_at: datetime | None
    sbom_stale: bool
    scan_state: ScanState
    inventory_changed_at: datetime | None
    github_repository: str | None
