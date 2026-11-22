"""Port: läuft gerade ein Scan oder GitHub-Abgleich?"""

from typing import Protocol


class JobActivity(Protocol):
    def is_busy(self) -> bool: ...
