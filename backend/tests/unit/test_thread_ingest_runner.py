import threading
from datetime import UTC, datetime

from app.application.ingest import IngestResult
from app.infrastructure.thread_ingest_runner import ThreadIngestRunner

_NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
_WAIT_SECONDS = 5


def _result() -> IngestResult:
    return IngestResult(components_scanned=2, findings_found=3, sources=[])


def test_start_runs_job_in_background() -> None:
    release = threading.Event()

    def job() -> IngestResult:
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

    def job() -> IngestResult:
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
    def job() -> IngestResult:
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
