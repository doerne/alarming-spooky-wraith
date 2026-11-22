import threading
from datetime import UTC, datetime

import pytest

from app.application.ingest import IngestResult
from app.domain.scan_run import ScanTrigger
from app.infrastructure.job_gate import JobGate
from app.infrastructure.thread_ingest_runner import ThreadIngestRunner

_NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
_WAIT_SECONDS = 5


def _result(_trigger: ScanTrigger = ScanTrigger.MANUAL) -> IngestResult:
    return IngestResult(components_scanned=2, findings_found=3, sources=[])


def test_start_runs_job_in_background() -> None:
    release = threading.Event()

    def job(_trigger: ScanTrigger) -> IngestResult:
        release.wait(_WAIT_SECONDS)
        return _result()

    runner = ThreadIngestRunner(job, lambda: _NOW)
    assert runner.start() is True
    assert runner.state().running is True
    assert runner.state().started_at == _NOW
    release.set()
    assert runner.wait(_WAIT_SECONDS)
    state = runner.state()
    assert state.running is False
    assert state.finished_at == _NOW
    assert state.components_scanned == 2
    assert state.findings_found == 3
    assert state.error is None


def test_second_start_is_rejected() -> None:
    release = threading.Event()
    calls: list[int] = []

    def job(_trigger: ScanTrigger) -> IngestResult:
        calls.append(1)
        release.wait(_WAIT_SECONDS)
        return _result()

    runner = ThreadIngestRunner(job, lambda: _NOW)
    assert runner.start() is True
    assert runner.start() is False
    release.set()
    assert runner.wait(_WAIT_SECONDS)
    assert calls == [1]


def test_job_error_is_reported() -> None:
    def job(_trigger: ScanTrigger) -> IngestResult:
        raise RuntimeError("password=geheim@db")

    runner = ThreadIngestRunner(job, lambda: _NOW)
    runner.start()
    assert runner.wait(_WAIT_SECONDS)
    state = runner.state()
    assert state.running is False
    assert state.error == "Lauf fehlgeschlagen (RuntimeError)"
    assert state.findings_found is None


def test_initial_state_is_idle() -> None:
    state = ThreadIngestRunner(_result, lambda: _NOW).state()
    assert state.running is False
    assert state.started_at is None


def test_start_passes_trigger_to_job() -> None:
    triggers: list[ScanTrigger] = []

    def job(trigger: ScanTrigger) -> IngestResult:
        triggers.append(trigger)
        return _result()

    runner = ThreadIngestRunner(job, lambda: _NOW)
    assert runner.start(ScanTrigger.SCHEDULE) is True
    assert runner.wait(_WAIT_SECONDS)
    assert runner.start() is True
    assert runner.wait(_WAIT_SECONDS)
    assert triggers == [ScanTrigger.SCHEDULE, ScanTrigger.MANUAL]


def test_failed_thread_start_releases_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    gate = JobGate()
    runner = ThreadIngestRunner(_result, lambda: _NOW, gate)

    def refuse(_self: threading.Thread) -> None:
        raise RuntimeError("can't start new thread")

    monkeypatch.setattr(threading.Thread, "start", refuse)
    with pytest.raises(RuntimeError):
        runner.start()
    assert runner.state().running is False
    monkeypatch.undo()
    assert runner.start() is True
    assert runner.wait(_WAIT_SECONDS)
