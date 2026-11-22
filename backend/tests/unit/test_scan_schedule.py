from datetime import UTC, datetime, timedelta

import pytest

from app.application.scan_schedule import (
    DecideCatchUp,
    ScanSchedule,
    parse_scan_schedule,
    start_catch_up_if_due,
)
from app.domain.scan_run import ScanOutcome, ScanRun, ScanTrigger
from tests.fakes import FakeIngestRunner, InMemoryUnitOfWork, uow_factory_for

_NOW = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)


def test_parse_valid_schedule() -> None:
    assert parse_scan_schedule("04:00", "Europe/Berlin") == ScanSchedule(4, 0, "Europe/Berlin")
    assert parse_scan_schedule("23:59", "UTC") == ScanSchedule(23, 59, "UTC")


@pytest.mark.parametrize("value", ["4:00", "24:00", "abc", "04:60", ""])
def test_parse_rejects_invalid_time(value: str) -> None:
    with pytest.raises(ValueError, match="SCAN_SCHEDULE_TIME") as error:
        parse_scan_schedule(value, "Europe/Berlin")
    assert repr(value) in str(error.value)


def test_parse_rejects_unknown_timezone() -> None:
    with pytest.raises(ValueError, match="SCAN_SCHEDULE_TIMEZONE") as error:
        parse_scan_schedule("04:00", "Mars/Base")
    assert "Mars/Base" in str(error.value)


def _add(
    uow: InMemoryUnitOfWork,
    hours_ago: int,
    *,
    outcome: ScanOutcome = ScanOutcome.OK,
    trigger: ScanTrigger = ScanTrigger.SCHEDULE,
    interrupted: bool = False,
) -> None:
    started = _NOW - timedelta(hours=hours_ago)
    run = uow.scan_runs.add(ScanRun(trigger=trigger, started_at=started))
    finished = run.interrupt(started) if interrupted else run.finish(outcome, started)
    uow.scan_runs.update(finished)


def _due(uow: InMemoryUnitOfWork) -> bool:
    return DecideCatchUp(uow, lambda: _NOW).execute()


def test_catch_up_without_any_run() -> None:
    assert _due(InMemoryUnitOfWork()) is True


def test_no_catch_up_after_recent_run() -> None:
    uow = InMemoryUnitOfWork()
    _add(uow, 23)
    assert _due(uow) is False


def test_catch_up_after_old_run() -> None:
    uow = InMemoryUnitOfWork()
    _add(uow, 25)
    assert _due(uow) is True


def test_recent_failed_run_counts_as_done() -> None:
    uow = InMemoryUnitOfWork()
    _add(uow, 2, outcome=ScanOutcome.FAILED)
    assert _due(uow) is False


def test_interrupted_run_does_not_count() -> None:
    uow = InMemoryUnitOfWork()
    _add(uow, 25)
    _add(uow, 1, interrupted=True)
    assert _due(uow) is True


def test_at_most_one_catch_up_per_day() -> None:
    uow = InMemoryUnitOfWork()
    _add(uow, 25)
    _add(uow, 3, trigger=ScanTrigger.CATCH_UP, interrupted=True)
    assert _due(uow) is False


def test_start_catch_up_when_due() -> None:
    runner = FakeIngestRunner()
    assert (
        start_catch_up_if_due(uow_factory_for(InMemoryUnitOfWork()), lambda: _NOW, runner) is True
    )
    assert runner.triggers == [ScanTrigger.CATCH_UP]


def test_no_start_when_not_due() -> None:
    uow = InMemoryUnitOfWork()
    _add(uow, 1)
    runner = FakeIngestRunner()
    assert start_catch_up_if_due(uow_factory_for(uow), lambda: _NOW, runner) is False
    assert runner.triggers == []
