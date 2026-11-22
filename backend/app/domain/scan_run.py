"""Ein Scan-Lauf über alle Anwendungen: manuell, geplant oder nachgeholt."""

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum

SCAN_MESSAGE_MAX_LENGTH = 500
INTERRUPTED_SCAN_MESSAGE = "durch Neustart abgebrochen"


class ScanTrigger(StrEnum):
    MANUAL = "manual"
    SCHEDULE = "schedule"
    CATCH_UP = "catch_up"


class ScanOutcome(StrEnum):
    """Ergebnis eines beendeten Laufs."""

    OK = "ok"
    INCOMPLETE = "incomplete"
    FAILED = "failed"


_USABLE_OUTCOMES = frozenset({ScanOutcome.OK, ScanOutcome.INCOMPLETE})


@dataclass(frozen=True)
class ScanCounts:
    """Zahlen eines beendeten Laufs."""

    components_scanned: int | None = None
    findings_found: int | None = None
    sources_with_errors: int = 0


@dataclass(frozen=True)
class ScanRun:
    trigger: ScanTrigger
    started_at: datetime
    id: int | None = None
    finished_at: datetime | None = None
    outcome: ScanOutcome | None = None
    components_scanned: int | None = None
    findings_found: int | None = None
    sources_with_errors: int = 0
    message: str = ""
    interrupted: bool = False

    @property
    def usable(self) -> bool:
        """Ob der Lauf einen verwertbaren Stand der CVE-Daten geliefert hat."""
        return self.finished_at is not None and self.outcome in _USABLE_OUTCOMES

    def finish(
        self,
        outcome: ScanOutcome,
        finished_at: datetime,
        *,
        counts: ScanCounts | None = None,
        message: str = "",
    ) -> "ScanRun":
        counts = counts or ScanCounts()
        return replace(
            self,
            outcome=outcome,
            finished_at=finished_at,
            components_scanned=counts.components_scanned,
            findings_found=counts.findings_found,
            sources_with_errors=counts.sources_with_errors,
            message=message[:SCAN_MESSAGE_MAX_LENGTH],
        )

    def interrupt(self, now: datetime) -> "ScanRun":
        """Lauf, den ein Neustart unterbrochen hat."""
        return replace(
            self.finish(ScanOutcome.FAILED, now, message=INTERRUPTED_SCAN_MESSAGE),
            interrupted=True,
        )
