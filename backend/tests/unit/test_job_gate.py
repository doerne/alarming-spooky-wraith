import threading
from datetime import UTC, datetime

from app.application.github_sync import SyncRequest
from app.application.ingest import IngestResult
from app.domain.scan_run import ScanTrigger
from app.infrastructure.job_gate import JobGate
from app.infrastructure.thread_ingest_runner import ThreadIngestRunner
from app.infrastructure.thread_sync_runner import ThreadSyncRunner

_NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)
_WAIT_SECONDS = 5


def _result(_trigger: ScanTrigger = ScanTrigger.MANUAL) -> IngestResult:
    return IngestResult(components_scanned=0, findings_found=0, sources=[])


def test_gate_admits_one_holder_at_a_time() -> None:
    gate = JobGate()
    assert gate.try_acquire() is True
    assert gate.try_acquire() is False
    gate.release()
    assert gate.try_acquire() is True


def test_scan_is_refused_while_sync_holds_the_gate() -> None:
    release = threading.Event()
    gate = JobGate()

    def sync_job(request: SyncRequest) -> bool:
        return release.wait(_WAIT_SECONDS)

    sync = ThreadSyncRunner(sync_job, lambda: _NOW, gate)
    scan = ThreadIngestRunner(_result, lambda: _NOW, gate)
    assert sync.start(SyncRequest(None, create_issues=False, min_level=None)) is True
    assert scan.start() is False
    release.set()
    assert sync.wait(_WAIT_SECONDS)
    assert scan.start() is True
    assert scan.wait(_WAIT_SECONDS)


def test_sync_is_refused_while_scan_holds_the_gate() -> None:
    release = threading.Event()
    gate = JobGate()

    def scan_job(_trigger: ScanTrigger) -> IngestResult:
        release.wait(_WAIT_SECONDS)
        return _result()

    scan = ThreadIngestRunner(scan_job, lambda: _NOW, gate)
    sync = ThreadSyncRunner(lambda _request: True, lambda: _NOW, gate)
    assert scan.start() is True
    assert sync.start(SyncRequest(1, create_issues=True, min_level=None)) is False
    release.set()
    assert scan.wait(_WAIT_SECONDS)


def test_gate_is_released_after_sync_error() -> None:
    def failing(request: SyncRequest) -> bool:
        raise RuntimeError("boom")

    gate = JobGate()
    sync = ThreadSyncRunner(failing, lambda: _NOW, gate)
    assert sync.start(SyncRequest(1, create_issues=False, min_level=None)) is True
    assert sync.wait(_WAIT_SECONDS)
    assert sync.state().error == "Abgleich fehlgeschlagen (RuntimeError)"
    assert gate.try_acquire() is True
