from app.application.ingest import IngestResult, run_scan_then_sync
from app.application.scan_progress import GITHUB_SYNC_STEP, StepState
from tests.fakes import RecordingProgress


def _result() -> IngestResult:
    return IngestResult(components_scanned=4, findings_found=2, sources=[])


def test_sync_runs_after_scan_and_scan_result_is_returned() -> None:
    order: list[str] = []

    def scan() -> IngestResult:
        order.append("scan")
        return _result()

    def sync() -> bool:
        order.append("sync")
        return True

    result = run_scan_then_sync(scan, sync)

    assert order == ["scan", "sync"]
    assert result.findings_found == 2


def test_sync_failure_is_logged_and_scan_result_is_kept() -> None:
    def failing_sync() -> bool:
        raise RuntimeError("GitHub weg")

    result = run_scan_then_sync(_result, failing_sync)

    assert result.components_scanned == 4


def _sync_states(progress: RecordingProgress) -> list[StepState]:
    return [state for key, state, _detail in progress.updates if key == GITHUB_SYNC_STEP]


def test_finished_sync_is_reported_done() -> None:
    progress = RecordingProgress()
    run_scan_then_sync(_result, lambda: True, progress)
    assert _sync_states(progress) == [StepState.RUNNING, StepState.DONE]


def test_unconfigured_sync_is_reported_skipped() -> None:
    progress = RecordingProgress()
    run_scan_then_sync(_result, lambda: False, progress)
    assert _sync_states(progress) == [StepState.RUNNING, StepState.SKIPPED]


def test_failing_sync_is_reported_failed_and_scan_result_is_kept() -> None:
    def failing_sync() -> bool:
        raise RuntimeError("GitHub weg")

    progress = RecordingProgress()
    result = run_scan_then_sync(_result, failing_sync, progress)

    assert _sync_states(progress) == [StepState.RUNNING, StepState.FAILED]
    assert progress.updates[-1][2] == "Abgleich fehlgeschlagen"
    assert result.findings_found == 2
