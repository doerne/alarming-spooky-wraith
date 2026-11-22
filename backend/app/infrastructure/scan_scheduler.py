"""Täglicher Scan über APScheduler (Hintergrund-Thread im Backend-Prozess)."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.application.ingest_runner import IngestRunner
from app.application.scan_schedule import ScanSchedule
from app.domain.scan_run import ScanTrigger

_logger = logging.getLogger(__name__)

_JOB_ID = "daily-scan"
# Startet der Scheduler verspätet (z. B. nach hoher Last), darf der Lauf bis zu 1 h später kommen.
_MISFIRE_GRACE_SECONDS = 3600


def run_scheduled_scan(runner: IngestRunner) -> None:
    """Job-Funktion: Fehler werden protokolliert, damit der Scheduler weiterläuft."""
    try:
        started = runner.start(ScanTrigger.SCHEDULE)
    except Exception:
        _logger.exception("Geplanter Scan konnte nicht starten")
        return
    if not started:
        _logger.info("Geplanter Scan übersprungen: es läuft bereits ein Lauf")


class ApsScanScheduler:
    def __init__(self, runner: IngestRunner, schedule: ScanSchedule) -> None:
        self._scheduler = BackgroundScheduler(timezone=schedule.timezone)
        self._scheduler.add_job(
            run_scheduled_scan,
            CronTrigger(hour=schedule.hour, minute=schedule.minute, timezone=schedule.timezone),
            args=[runner],
            id=_JOB_ID,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=_MISFIRE_GRACE_SECONDS,
        )

    def start(self, *, paused: bool = False) -> None:
        self._scheduler.start(paused=paused)

    def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)

    def job_trigger_description(self) -> str:
        return repr(self._scheduler.get_job(_JOB_ID).trigger)
