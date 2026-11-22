import logging

import pytest

from app.application.ingest_runner import IngestRunState
from app.application.scan_schedule import ScanSchedule
from app.domain.scan_run import ScanTrigger
from app.infrastructure.scan_scheduler import ApsScanScheduler, run_scheduled_scan
from tests.fakes import FakeIngestRunner


class _BrokenRunner(FakeIngestRunner):
    def start(self, trigger: ScanTrigger = ScanTrigger.MANUAL) -> bool:
        raise RuntimeError("kaputt")


def test_registers_one_daily_job_with_time_and_zone() -> None:
    scheduler = ApsScanScheduler(FakeIngestRunner(), ScanSchedule(4, 0, "Europe/Berlin"))
    scheduler.start(paused=True)
    try:
        description = scheduler.job_trigger_description()
    finally:
        scheduler.shutdown()
    assert "hour='4'" in description
    assert "minute='0'" in description
    assert "Europe/Berlin" in description


def test_scheduled_job_starts_scan_with_schedule_trigger() -> None:
    runner = FakeIngestRunner()
    run_scheduled_scan(runner)
    assert runner.triggers == [ScanTrigger.SCHEDULE]


def test_busy_runner_is_logged_as_skipped(caplog: pytest.LogCaptureFixture) -> None:
    runner = FakeIngestRunner(IngestRunState(running=True))
    with caplog.at_level(logging.INFO):
        run_scheduled_scan(runner)
    assert "Geplanter Scan übersprungen" in caplog.text


def test_runner_error_is_logged_not_raised(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.ERROR):
        run_scheduled_scan(_BrokenRunner())
    assert "Geplanter Scan konnte nicht starten" in caplog.text
