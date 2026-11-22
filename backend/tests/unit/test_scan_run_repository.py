"""Gleiche Erwartungen an das SQLAlchemy-Repository und den In-Memory-Fake."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.domain.ports import ScanRunRepository
from app.domain.scan_run import ScanCounts, ScanOutcome, ScanRun, ScanTrigger
from app.infrastructure import models  # noqa: F401  (Modelle registrieren)
from app.infrastructure.database import Base
from app.infrastructure.scan_run_repository import SqlAlchemyScanRunRepository
from tests.fakes import InMemoryScanRunRepository

_DAY = datetime(2026, 11, 22, 4, 0, tzinfo=UTC)


@pytest.fixture(params=["sql", "memory"])
def runs(request: pytest.FixtureRequest) -> Iterator[ScanRunRepository]:
    if request.param == "memory":
        yield InMemoryScanRunRepository()
        return
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield SqlAlchemyScanRunRepository(session)


def _finished(
    runs: ScanRunRepository,
    hours_ago: int,
    outcome: ScanOutcome,
    trigger: ScanTrigger = ScanTrigger.SCHEDULE,
) -> ScanRun:
    started = _DAY - timedelta(hours=hours_ago)
    run = runs.add(ScanRun(trigger=trigger, started_at=started))
    return runs.update(run.finish(outcome, started + timedelta(minutes=10)))


def test_add_assigns_id_and_update_round_trips(runs: ScanRunRepository) -> None:
    run = runs.add(ScanRun(trigger=ScanTrigger.MANUAL, started_at=_DAY))
    assert run.id is not None
    runs.update(
        run.finish(
            ScanOutcome.INCOMPLETE, _DAY, counts=ScanCounts(sources_with_errors=2), message="m"
        )
    )
    latest = runs.latest_finished()
    assert latest is not None
    assert latest.id == run.id
    assert latest.outcome == ScanOutcome.INCOMPLETE
    assert latest.sources_with_errors == 2
    assert latest.message == "m"


def test_latest_usable_skips_newer_failed_run(runs: ScanRunRepository) -> None:
    usable = _finished(runs, 30, ScanOutcome.OK)
    _finished(runs, 5, ScanOutcome.FAILED)
    latest_usable = runs.latest_usable()
    latest = runs.latest_finished()
    assert latest_usable is not None
    assert latest_usable.id == usable.id
    assert latest is not None
    assert latest.outcome == ScanOutcome.FAILED


def test_latest_regular_finished_skips_interrupted_run(runs: ScanRunRepository) -> None:
    regular = _finished(runs, 30, ScanOutcome.FAILED)
    interrupted = runs.add(ScanRun(trigger=ScanTrigger.SCHEDULE, started_at=_DAY))
    runs.update(interrupted.interrupt(_DAY + timedelta(minutes=1)))
    latest = runs.latest_regular_finished()
    assert latest is not None
    assert latest.id == regular.id


def test_latest_started_filters_by_trigger(runs: ScanRunRepository) -> None:
    catch_up = _finished(runs, 10, ScanOutcome.OK, ScanTrigger.CATCH_UP)
    _finished(runs, 2, ScanOutcome.OK, ScanTrigger.MANUAL)
    latest = runs.latest_started(ScanTrigger.CATCH_UP)
    assert latest is not None
    assert latest.id == catch_up.id
    assert runs.latest_started(ScanTrigger.SCHEDULE) is None


def test_list_unfinished_returns_only_open_runs(runs: ScanRunRepository) -> None:
    _finished(runs, 10, ScanOutcome.OK)
    open_run = runs.add(ScanRun(trigger=ScanTrigger.MANUAL, started_at=_DAY))
    assert [run.id for run in runs.list_unfinished()] == [open_run.id]


def test_empty_repository_has_no_latest_runs(runs: ScanRunRepository) -> None:
    assert runs.latest_finished() is None
    assert runs.latest_usable() is None
    assert runs.latest_regular_finished() is None


def test_read_timestamps_are_utc_aware(runs: ScanRunRepository) -> None:
    _finished(runs, 1, ScanOutcome.OK)
    latest = runs.latest_finished()
    assert latest is not None
    assert latest.started_at.tzinfo == UTC
    assert latest.finished_at is not None
    assert latest.finished_at.tzinfo == UTC
