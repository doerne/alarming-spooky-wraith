"""Zeitplan des täglichen Scans und Nachholen verpasster Läufe."""

import re
from dataclasses import dataclass
from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.application.ingest import Clock
from app.application.ingest_runner import IngestRunner
from app.application.unit_of_work import UnitOfWork, UnitOfWorkFactory
from app.domain.scan_run import ScanTrigger

CATCH_UP_AFTER = timedelta(hours=24)
_TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


@dataclass(frozen=True)
class ScanSchedule:
    hour: int
    minute: int
    timezone: str


def _valid_timezone(timezone: str) -> bool:
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def parse_scan_schedule(time_text: str, timezone: str) -> ScanSchedule:
    """Prüft die Werte aus der Umgebung; Fehler nennen Variable und Wert."""
    match = _TIME_PATTERN.match(time_text)
    if match is None:
        raise ValueError(f"SCAN_SCHEDULE_TIME muss HH:MM sein, ist aber {time_text!r}")
    if not _valid_timezone(timezone):
        raise ValueError(f"SCAN_SCHEDULE_TIMEZONE ist keine bekannte Zeitzone: {timezone!r}")
    return ScanSchedule(int(match.group(1)), int(match.group(2)), timezone)


class DecideCatchUp:
    """Nachholen, wenn seit 24 h kein Lauf regulär endete und heute noch nicht nachgeholt wurde."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def execute(self) -> bool:
        cutoff = self._clock() - CATCH_UP_AFTER
        last_catch_up = self._uow.scan_runs.latest_started(ScanTrigger.CATCH_UP)
        if last_catch_up is not None and last_catch_up.started_at > cutoff:
            return False
        last_regular = self._uow.scan_runs.latest_regular_finished()
        return last_regular is None or last_regular.started_at <= cutoff


def start_catch_up_if_due(
    uow_factory: UnitOfWorkFactory, clock: Clock, runner: IngestRunner
) -> bool:
    with uow_factory() as uow:
        due = DecideCatchUp(uow, clock).execute()
    return due and runner.start(ScanTrigger.CATCH_UP)
