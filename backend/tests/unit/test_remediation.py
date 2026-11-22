from datetime import UTC, datetime, timedelta

from app.domain.remediation import ClosureKind, closure_kind_of, compute_deadlines, due_at
from app.domain.vulnerability import Finding, FindingStatus, ResolutionSource, RiskScore, Severity

NOW = datetime(2026, 12, 1, 12, 0, tzinfo=UTC)


def make_finding(
    status: FindingStatus = FindingStatus.OPEN,
    first_seen_at: datetime | None = None,
    level: Severity = Severity.MITTEL,
    resolved_by: ResolutionSource | None = None,
) -> Finding:
    return Finding(
        advisory_id="CVE-2026-0001",
        component_id=1,
        application_id=1,
        found_version="1.0",
        risk=RiskScore(value=50, level=level, rationale=""),
        status=status,
        first_seen_at=first_seen_at,
        resolved_by=resolved_by,
    )


def test_closure_kind_per_status_and_source() -> None:
    fixed = FindingStatus.FIXED
    assert closure_kind_of(make_finding(fixed, resolved_by=ResolutionSource.SBOM)) == (
        ClosureKind.FIXED_CONFIRMED
    )
    assert closure_kind_of(make_finding(fixed, resolved_by=ResolutionSource.REPORTED)) == (
        ClosureKind.FIXED_REPORTED
    )
    assert closure_kind_of(make_finding(fixed)) == ClosureKind.FIXED_MANUAL
    assert closure_kind_of(make_finding(FindingStatus.ACCEPTED)) == ClosureKind.ACCEPTED
    assert closure_kind_of(make_finding(FindingStatus.FALSE_POSITIVE)) == (
        ClosureKind.FALSE_POSITIVE
    )
    assert closure_kind_of(make_finding(FindingStatus.IN_PROGRESS)) is None


def test_due_at_starts_at_deadline_start_for_old_or_unknown_first_seen() -> None:
    old = make_finding(first_seen_at=datetime(2025, 11, 1, tzinfo=UTC), level=Severity.HOCH)
    assert due_at(old) == datetime(2026, 12, 22, tzinfo=UTC)
    unknown = make_finding(first_seen_at=None, level=Severity.KRITISCH)
    assert due_at(unknown) == datetime(2026, 11, 29, tzinfo=UTC)


def test_due_at_uses_first_seen_after_start() -> None:
    seen = datetime(2026, 11, 25, 8, 0, tzinfo=UTC)
    assert due_at(make_finding(first_seen_at=seen, level=Severity.MITTEL)) == seen + timedelta(
        days=90
    )


def test_exactly_due_counts_as_overdue_not_due_soon() -> None:
    finding = make_finding(first_seen_at=NOW - timedelta(days=7), level=Severity.KRITISCH)
    summary = compute_deadlines([finding], NOW)
    assert (summary.overdue, summary.due_soon) == (1, 0)
    assert summary.overdue_by_severity == {
        Severity.KRITISCH: 1,
        Severity.HOCH: 0,
        Severity.MITTEL: 0,
        Severity.NIEDRIG: 0,
    }


def test_due_soon_window_and_next_due() -> None:
    # Erstsichtungen nach DEADLINE_START, damit die Frist ab first_seen_at läuft.
    later_now = datetime(2027, 1, 15, 12, 0, tzinfo=UTC)
    soon = make_finding(first_seen_at=later_now - timedelta(days=25), level=Severity.HOCH)
    later = make_finding(first_seen_at=later_now - timedelta(days=10), level=Severity.HOCH)
    summary = compute_deadlines([later, soon], later_now)
    assert (summary.overdue, summary.due_soon) == (0, 1)
    assert summary.next_due_at == later_now + timedelta(days=5)


def test_closed_findings_never_count_and_in_progress_does() -> None:
    old = NOW - timedelta(days=60)
    overdue_closed = make_finding(
        FindingStatus.ACCEPTED, first_seen_at=old, level=Severity.KRITISCH
    )
    overdue_working = make_finding(
        FindingStatus.IN_PROGRESS, first_seen_at=old, level=Severity.KRITISCH
    )
    assert compute_deadlines([overdue_closed, overdue_working], NOW).overdue == 1


def test_no_open_findings() -> None:
    summary = compute_deadlines([], NOW)
    assert (summary.overdue, summary.due_soon, summary.next_due_at) == (0, 0, None)
