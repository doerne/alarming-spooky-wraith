"""Startet den Ingest in einem Hintergrund-Thread; immer nur ein Lauf gleichzeitig.

Der Zustand liegt im Speicher des Prozesses (ein uvicorn-Worker).
"""

import logging
import threading
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from app.application.ingest import IngestResult
from app.application.ingest_runner import IngestRunState

_logger = logging.getLogger(__name__)


class ThreadIngestRunner:
    def __init__(self, job: Callable[[], IngestResult], clock: Callable[[], datetime]) -> None:
        self._job = job
        self._clock = clock
        self._lock = threading.Lock()
        self._state = IngestRunState(running=False)
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        with self._lock:
            if self._state.running:
                return False
            self._state = IngestRunState(running=True, started_at=self._clock())
            self._thread = threading.Thread(target=self._run, name="ingest", daemon=True)
            self._thread.start()
            return True

    def state(self) -> IngestRunState:
        with self._lock:
            return self._state

    def wait(self, timeout: float) -> bool:
        """Wartet auf das Ende des Laufs (für Tests und sauberes Herunterfahren)."""
        thread = self._thread
        if thread is not None:
            thread.join(timeout)
        return not self.state().running

    def _run(self) -> None:
        try:
            result = self._job()
        except Exception as error:
            # Details nur ins Log: Ausnahmen (z. B. der DB) können Interna enthalten.
            _logger.exception("Ingest-Lauf fehlgeschlagen")
            self._finish(error=f"Lauf fehlgeschlagen ({type(error).__name__})")
            return
        self._finish(
            components_scanned=result.components_scanned, findings_found=result.findings_found
        )

    def _finish(
        self,
        *,
        components_scanned: int | None = None,
        findings_found: int | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            self._state = replace(
                self._state,
                running=False,
                finished_at=self._clock(),
                components_scanned=components_scanned,
                findings_found=findings_found,
                error=error,
            )
