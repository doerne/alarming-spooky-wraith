"""Startet den Ingest in einem Hintergrund-Thread; immer nur ein Lauf gleichzeitig.

Der Zustand liegt im Speicher des Prozesses (ein uvicorn-Worker).
"""

import logging
import threading
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import datetime

from app.application.ingest import IngestResult
from app.application.ingest_runner import IngestRunState
from app.application.scan_progress import ScanStep
from app.domain.scan_run import ScanTrigger
from app.infrastructure.job_gate import JobGate
from app.infrastructure.scan_progress_tracker import ScanProgressTracker

_logger = logging.getLogger(__name__)
_ABORTED_STEP_DETAIL = "Lauf abgebrochen"


class ThreadIngestRunner:
    def __init__(
        self,
        job: Callable[[ScanTrigger], IngestResult],
        clock: Callable[[], datetime],
        gate: JobGate | None = None,
        progress: ScanProgressTracker | None = None,
        steps: Callable[[], Sequence[ScanStep]] = list,
    ) -> None:
        self._job = job
        self._clock = clock
        self._gate = gate or JobGate()
        self._progress = progress or ScanProgressTracker()
        self._steps = steps
        self._lock = threading.Lock()
        self._state = IngestRunState(running=False)
        self._thread: threading.Thread | None = None

    def start(self, trigger: ScanTrigger = ScanTrigger.MANUAL) -> bool:
        with self._lock:
            if self._state.running or not self._gate.try_acquire():
                return False
            previous = self._state
            self._progress.begin(self._steps())
            self._state = IngestRunState(running=True, started_at=self._clock())
            self._thread = threading.Thread(
                target=self._run, args=(trigger,), name="ingest", daemon=True
            )
            try:
                self._thread.start()
            except Exception:
                # Sonst bliebe die Sperre belegt und kein späterer Scan liefe mehr an.
                self._state = previous
                self._gate.release()
                raise
            return True

    def state(self) -> IngestRunState:
        with self._lock:
            return replace(self._state, steps=self._progress.snapshot())

    def wait(self, timeout: float) -> bool:
        """Wartet auf das Ende des Laufs (für Tests und sauberes Herunterfahren)."""
        thread = self._thread
        if thread is not None:
            thread.join(timeout)
        return not self.state().running

    def _run(self, trigger: ScanTrigger) -> None:
        try:
            result = self._job(trigger)
        except Exception as error:
            # Details nur ins Log: Ausnahmen (z. B. der DB) können Interna enthalten.
            _logger.exception("Ingest-Lauf fehlgeschlagen")
            self._progress.fail_running(_ABORTED_STEP_DETAIL)
            self._finish(error=f"Lauf fehlgeschlagen ({type(error).__name__})")
        else:
            self._finish(
                components_scanned=result.components_scanned, findings_found=result.findings_found
            )
        finally:
            self._gate.release()

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
