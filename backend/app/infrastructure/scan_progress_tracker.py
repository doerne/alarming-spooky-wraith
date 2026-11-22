"""Hält den Fortschritt des laufenden Scans im Speicher; Scan-Thread schreibt, API liest."""

import threading
from collections.abc import Sequence
from dataclasses import replace

from app.application.scan_progress import ScanStep, StepState


class ScanProgressTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._steps: tuple[ScanStep, ...] = ()

    def begin(self, steps: Sequence[ScanStep]) -> None:
        with self._lock:
            self._steps = tuple(ScanStep(step.key, step.label) for step in steps)

    def update(self, key: str, state: StepState, detail: str = "") -> None:
        with self._lock:
            self._steps = tuple(
                replace(step, state=state, detail=detail) if step.key == key else step
                for step in self._steps
            )

    def snapshot(self) -> tuple[ScanStep, ...]:
        with self._lock:
            return self._steps
