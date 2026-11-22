"""Port: exklusiver Zugriff auf die Job-Sperre (Scan, GitHub-Abgleich, Löschen)."""

from typing import Protocol


class JobActivity(Protocol):
    def try_acquire(self) -> bool: ...

    def release(self) -> None: ...


class _IdleActivity:
    """Immer frei: für Betrieb ohne Hintergrundjobs (z. B. Tests)."""

    def try_acquire(self) -> bool:
        return True

    def release(self) -> None:
        return None


IDLE_ACTIVITY: JobActivity = _IdleActivity()
