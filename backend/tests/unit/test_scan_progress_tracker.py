from app.application.scan_progress import ScanStep, StepState
from app.infrastructure.scan_progress_tracker import ScanProgressTracker


def _tracker() -> ScanProgressTracker:
    tracker = ScanProgressTracker()
    tracker.begin([ScanStep("osv", "OSV"), ScanStep("nvd", "NVD")])
    return tracker


def test_begin_sets_every_step_pending() -> None:
    tracker = ScanProgressTracker()
    tracker.begin([ScanStep("osv", "OSV", StepState.DONE, "alt")])
    assert tracker.snapshot() == (ScanStep("osv", "OSV"),)


def test_update_changes_exactly_one_step() -> None:
    tracker = _tracker()
    tracker.update("nvd", StepState.SKIPPED, "API-Key fehlt")
    assert tracker.snapshot() == (
        ScanStep("osv", "OSV"),
        ScanStep("nvd", "NVD", StepState.SKIPPED, "API-Key fehlt"),
    )


def test_unknown_key_is_ignored() -> None:
    tracker = _tracker()
    tracker.update("ghsa", StepState.DONE)
    assert tracker.snapshot() == (ScanStep("osv", "OSV"), ScanStep("nvd", "NVD"))


def test_snapshot_is_a_copy() -> None:
    tracker = _tracker()
    before = tracker.snapshot()
    tracker.update("osv", StepState.RUNNING)
    assert before[0].state == StepState.PENDING
    assert tracker.snapshot()[0].state == StepState.RUNNING


def test_fail_running_marks_only_running_steps_failed() -> None:
    tracker = _tracker()
    tracker.update("osv", StepState.RUNNING)
    tracker.fail_running("Lauf abgebrochen")
    assert tracker.snapshot() == (
        ScanStep("osv", "OSV", StepState.FAILED, "Lauf abgebrochen"),
        ScanStep("nvd", "NVD"),
    )
