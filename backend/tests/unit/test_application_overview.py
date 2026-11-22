from datetime import UTC, datetime, timedelta

from app.domain.application_overview import (
    SBOM_STALE_AFTER_DAYS,
    ScanState,
    count_open_by_severity,
    is_sbom_stale,
    scan_state,
)
from app.domain.vulnerability import Finding, FindingStatus, RiskScore, Severity

_NOW = datetime(2026, 11, 22, 10, 0, tzinfo=UTC)
_SCAN_START = datetime(2026, 11, 22, 4, 0, tzinfo=UTC)


def test_without_usable_scan_is_never_scanned() -> None:
    assert scan_state(None, None) == ScanState.NEVER_SCANNED
    assert scan_state(_NOW, None) == ScanState.NEVER_SCANNED


def test_unchanged_inventory_is_current() -> None:
    assert scan_state(None, _SCAN_START) == ScanState.CURRENT
    assert scan_state(_SCAN_START, _SCAN_START) == ScanState.CURRENT


def test_change_after_scan_start_is_changed() -> None:
    changed = _SCAN_START + timedelta(seconds=1)
    assert scan_state(changed, _SCAN_START) == ScanState.CHANGED_SINCE_SCAN


def test_missing_sbom_is_stale() -> None:
    assert is_sbom_stale(None, _NOW) is True


def test_sbom_stale_after_thirty_days() -> None:
    limit = _NOW - timedelta(days=SBOM_STALE_AFTER_DAYS)
    assert is_sbom_stale(limit, _NOW) is False
    assert is_sbom_stale(limit - timedelta(seconds=1), _NOW) is True


def _finding(level: Severity, status: FindingStatus = FindingStatus.OPEN) -> Finding:
    return Finding(
        advisory_id="CVE-1",
        component_id=1,
        application_id=1,
        found_version="1",
        risk=RiskScore(value=50, level=level, rationale="r"),
        status=status,
    )


def test_open_counts_always_list_all_four_levels() -> None:
    counts = count_open_by_severity(
        [_finding(Severity.HOCH), _finding(Severity.HOCH, FindingStatus.ACCEPTED)]
    )
    assert counts == {
        Severity.KRITISCH: 0,
        Severity.HOCH: 1,
        Severity.MITTEL: 0,
        Severity.NIEDRIG: 0,
    }
