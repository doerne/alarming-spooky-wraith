from app.application.ingest import IngestResult, run_scan_then_sync


def _result() -> IngestResult:
    return IngestResult(components_scanned=4, findings_found=2, sources=[])


def test_sync_runs_after_scan_and_scan_result_is_returned() -> None:
    order: list[str] = []

    def scan() -> IngestResult:
        order.append("scan")
        return _result()

    result = run_scan_then_sync(scan, lambda: order.append("sync"))

    assert order == ["scan", "sync"]
    assert result.findings_found == 2


def test_sync_failure_is_logged_and_scan_result_is_kept() -> None:
    def failing_sync() -> None:
        raise RuntimeError("GitHub weg")

    result = run_scan_then_sync(_result, failing_sync)

    assert result.components_scanned == 4
