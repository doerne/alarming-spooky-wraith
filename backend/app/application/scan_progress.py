"""Port für den Fortschritt eines Scans: ein Schritt je Quelle, dann Speichern und Abgleich."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from app.domain.sources import SourceDescriptor

PERSIST_STEP = "persist"
GITHUB_SYNC_STEP = "github-sync"


class StepState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class ScanStep:
    key: str
    label: str
    state: StepState = StepState.PENDING
    detail: str = ""


class ScanProgress(Protocol):
    def begin(self, steps: Sequence[ScanStep]) -> None: ...

    def update(self, key: str, state: StepState, detail: str = "") -> None: ...


class _NoProgress:
    """Standard, wenn niemand den Fortschritt anzeigt."""

    def begin(self, steps: Sequence[ScanStep]) -> None:
        pass

    def update(self, key: str, state: StepState, detail: str = "") -> None:
        pass


NO_PROGRESS: ScanProgress = _NoProgress()


def initial_steps(descriptors: Sequence[SourceDescriptor]) -> list[ScanStep]:
    """Alle Quellen in Registry-Reihenfolge, danach Speichern und GitHub-Abgleich."""
    sources = [ScanStep(descriptor.key, descriptor.name) for descriptor in descriptors]
    return [
        *sources,
        ScanStep(PERSIST_STEP, "Funde speichern"),
        ScanStep(GITHUB_SYNC_STEP, "GitHub-Abgleich"),
    ]
