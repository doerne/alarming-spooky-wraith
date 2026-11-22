"""Startet den GitHub-Abgleich in einem Hintergrund-Thread; Sperre mit dem Scan geteilt."""

import logging
import threading
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from app.application.github_sync import SyncRequest, SyncRunState
from app.infrastructure.job_gate import JobGate

_logger = logging.getLogger(__name__)


class ThreadSyncRunner:
    def __init__(
        self,
        job: Callable[[SyncRequest], bool],
        clock: Callable[[], datetime],
        gate: JobGate,
    ) -> None:
        self._job = job
        self._clock = clock
        self._gate = gate
        self._lock = threading.Lock()
        self._state = SyncRunState(running=False)
        self._thread: threading.Thread | None = None

    def start(self, request: SyncRequest) -> bool:
        with self._lock:
            if self._state.running or not self._gate.try_acquire():
                return False
            self._state = SyncRunState(running=True, started_at=self._clock())
            self._thread = threading.Thread(
                target=self._run, args=(request,), name="github-sync", daemon=True
            )
            self._thread.start()
            return True

    def state(self) -> SyncRunState:
        with self._lock:
            return self._state

    def wait(self, timeout: float) -> bool:
        """Wartet auf das Ende des Laufs (für Tests und sauberes Herunterfahren)."""
        thread = self._thread
        if thread is not None:
            thread.join(timeout)
        return not self.state().running

    def _run(self, request: SyncRequest) -> None:
        try:
            self._job(request)
        except Exception as error:
            # Details nur ins Log: Ausnahmen können Interna enthalten.
            _logger.exception("GitHub-Abgleich fehlgeschlagen")
            self._finish(error=f"Abgleich fehlgeschlagen ({type(error).__name__})")
        else:
            self._finish()
        finally:
            self._gate.release()

    def _finish(self, *, error: str | None = None) -> None:
        with self._lock:
            self._state = replace(
                self._state, running=False, finished_at=self._clock(), error=error
            )
