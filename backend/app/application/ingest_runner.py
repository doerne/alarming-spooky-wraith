"""Port für den Ingest-Lauf im Hintergrund."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class IngestRunState:
    """Zustand des aktuellen bzw. letzten Laufs."""

    running: bool
    started_at: datetime | None = None
    finished_at: datetime | None = None
    components_scanned: int | None = None
    findings_found: int | None = None
    error: str | None = None


class IngestRunner(Protocol):
    def start(self) -> bool:
        """Startet einen Lauf. False, wenn schon einer läuft."""
        ...

    def state(self) -> IngestRunState: ...
