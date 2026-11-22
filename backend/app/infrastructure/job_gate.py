"""Gemeinsame Sperre für Scan und GitHub-Abgleich: nie beides gleichzeitig."""

import threading


class JobGate:
    """Ein Besitzer zur Zeit; ``try_acquire`` wartet nicht."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def try_acquire(self) -> bool:
        return self._lock.acquire(blocking=False)

    def release(self) -> None:
        self._lock.release()
