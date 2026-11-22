from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest

from app.application.ingest import IngestResult, SourceRunResult
from app.application.scan_runs import (
    GetScanHistory,
    ResetInterruptedScans,
    outcome_of,
    reset_interrupted_runs,
    run_recorded_scan,
)
from app.domain.scan_run import INTERRUPTED_SCAN_MESSAGE, ScanOutcome, ScanRun, ScanTrigger
from app.domain.sources import RunStatus, SourceSetting
from tests.fakes import InMemoryUnitOfWork

_NOW = datetime(2026, 11, 22, 4, 0, tzinfo=UTC)


def _source(key: str, status: RunStatus, *, complete: bool = True) -> SourceRunResult:
    return SourceRunResult(key, status, findings=0, message="", complete=complete)


def _result(*sources: SourceRunResult) -> IngestResult:
    return IngestResult(components_scanned=4, findings_found=9, sources=list(sources))


@pytest.fixture
def uow() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


def _factory(uow: InMemoryUnitOfWork):  # type: ignore[no-untyped-def]
    @contextmanager
    def factory() -> Iterator[InMemoryUnitOfWork]:
        yield uow

    return factory


def test_outcome_ok_when_all_sources_succeed() -> None:
    result = _result(_source("osv", RunStatus.OK), _source("snyk", RunStatus.SKIPPED))
    assert outcome_of(result) == (ScanOutcome.OK, 0, "")


def test_outcome_incomplete_names_unreliable_sources() -> None:
    result = _result(
        _source("osv", RunStatus.OK),
        _source("nvd", RunStatus.ERROR),
        _source("snyk", RunStatus.OK, complete=False),
    )
    assert outcome_of(result) == (ScanOutcome.INCOMPLETE, 2, "2 Quellen mit Fehlern: nvd, snyk")


def test_recorded_scan_stores_finished_run(uow: InMemoryUnitOfWork) -> None:
    result = run_recorded_scan(
        _factory(uow),
        lambda: _NOW,
        lambda: _result(_source("osv", RunStatus.OK)),
        ScanTrigger.SCHEDULE,
    )
    assert result.findings_found == 9
    run = uow.scan_runs.latest_finished()
    assert run is not None
    assert run.trigger == ScanTrigger.SCHEDULE
    assert run.outcome == ScanOutcome.OK
    assert run.components_scanned == 4
    assert run.findings_found == 9
    assert uow.scan_runs.list_unfinished() == []


def test_recorded_scan_marks_failed_run_and_reraises(uow: InMemoryUnitOfWork) -> None:
    def failing() -> IngestResult:
        raise RuntimeError("db weg")

    with pytest.raises(RuntimeError):
        run_recorded_scan(_factory(uow), lambda: _NOW, failing, ScanTrigger.MANUAL)
    run = uow.scan_runs.latest_finished()
    assert run is not None
    assert run.outcome == ScanOutcome.FAILED
    assert run.message == "Lauf fehlgeschlagen (RuntimeError)"
    assert uow.scan_runs.list_unfinished() == []


def test_reset_interrupts_unfinished_runs_only(uow: InMemoryUnitOfWork) -> None:
    finished = uow.scan_runs.add(ScanRun(trigger=ScanTrigger.MANUAL, started_at=_NOW))
    uow.scan_runs.update(finished.finish(ScanOutcome.OK, _NOW))
    uow.scan_runs.add(ScanRun(trigger=ScanTrigger.SCHEDULE, started_at=_NOW))
    later = _NOW + timedelta(hours=1)
    assert ResetInterruptedScans(uow, lambda: later).execute() == 1
    assert uow.scan_runs.list_unfinished() == []
    latest = uow.scan_runs.latest_finished()
    assert latest is not None
    assert latest.interrupted is True
    assert latest.message == INTERRUPTED_SCAN_MESSAGE
    assert latest.finished_at == later
    assert uow.commits == 1


def test_history_separates_last_run_from_last_usable(uow: InMemoryUnitOfWork) -> None:
    usable = uow.scan_runs.add(ScanRun(trigger=ScanTrigger.SCHEDULE, started_at=_NOW))
    uow.scan_runs.update(usable.finish(ScanOutcome.OK, _NOW))
    failed = uow.scan_runs.add(
        ScanRun(trigger=ScanTrigger.MANUAL, started_at=_NOW + timedelta(hours=2))
    )
    uow.scan_runs.update(failed.finish(ScanOutcome.FAILED, _NOW + timedelta(hours=2)))
    history = GetScanHistory(uow).execute()
    assert history.last_run is not None
    assert history.last_run.id == failed.id
    assert history.last_usable_run is not None
    assert history.last_usable_run.id == usable.id


def test_startup_reset_cleans_sources_and_scan_runs(uow: InMemoryUnitOfWork) -> None:
    uow.source_settings.save(SourceSetting(source_key="osv", last_status=RunStatus.RUNNING))
    uow.scan_runs.add(ScanRun(trigger=ScanTrigger.SCHEDULE, started_at=_NOW))
    reset_interrupted_runs(_factory(uow), lambda: _NOW)
    osv = uow.source_settings.get("osv")
    assert osv is not None
    assert osv.last_status == RunStatus.ERROR
    assert uow.scan_runs.list_unfinished() == []
