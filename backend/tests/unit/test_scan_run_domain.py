from datetime import UTC, datetime

from app.domain.scan_run import (
    INTERRUPTED_SCAN_MESSAGE,
    SCAN_MESSAGE_MAX_LENGTH,
    ScanCounts,
    ScanOutcome,
    ScanRun,
    ScanTrigger,
)

_START = datetime(2026, 11, 22, 4, 0, tzinfo=UTC)
_END = datetime(2026, 11, 22, 4, 12, tzinfo=UTC)


def _run() -> ScanRun:
    return ScanRun(trigger=ScanTrigger.SCHEDULE, started_at=_START)


def test_unfinished_run_is_not_usable() -> None:
    assert _run().usable is False


def test_finished_ok_run_is_usable() -> None:
    run = _run().finish(
        ScanOutcome.OK, _END, counts=ScanCounts(components_scanned=3, findings_found=7)
    )
    assert run.finished_at == _END
    assert run.components_scanned == 3
    assert run.findings_found == 7
    assert run.usable is True


def test_incomplete_run_is_usable() -> None:
    run = _run().finish(ScanOutcome.INCOMPLETE, _END, counts=ScanCounts(sources_with_errors=2))
    assert run.usable is True
    assert run.sources_with_errors == 2


def test_failed_run_is_not_usable() -> None:
    assert _run().finish(ScanOutcome.FAILED, _END).usable is False


def test_finish_shortens_long_message() -> None:
    run = _run().finish(ScanOutcome.FAILED, _END, message="x" * 600)
    assert len(run.message) == SCAN_MESSAGE_MAX_LENGTH


def test_interrupt_marks_run_as_failed_and_interrupted() -> None:
    run = _run().interrupt(_END)
    assert run.outcome == ScanOutcome.FAILED
    assert run.interrupted is True
    assert run.message == INTERRUPTED_SCAN_MESSAGE
    assert run.finished_at == _END
