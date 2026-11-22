"""Port für den Ingest-Lauf im Hintergrund."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.application.scan_progress import ScanStep
from app.domain.scan_run import ScanTrigger


@dataclass(frozen=True)
class IngestRunState:
    """Zustand des aktuellen bzw. letzten Laufs."""

    running: bool
    started_at: datetime | None = None
    finished_at: datetime | None = None
    components_scanned: int | None = None
    findings_found: int | None = None
    error: str | None = None
    steps: tuple[ScanStep, ...] = ()


class IngestRunner(Protocol):
    def start(self, trigger: ScanTrigger = ScanTrigger.MANUAL) -> bool:
        """Startet einen Lauf. False, wenn schon einer läuft."""
        ...

    def state(self) -> IngestRunState: ...
