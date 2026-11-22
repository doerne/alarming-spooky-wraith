from datetime import UTC, date, datetime, timedelta

from app.domain.finding_trend import compute_trend
from app.domain.remediation import ClosureKind
from app.domain.vulnerability import (
    Finding,
    FindingStatus,
    ResolutionSource,
    RiskScore,
    Severity,
)

NOW = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)


def make_finding(
    status: FindingStatus = FindingStatus.OPEN,
    first_seen_at: datetime | None = None,
    closed_at: datetime | None = None,
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
        closed_at=closed_at,
        resolved_by=resolved_by,
    )


def test_week_starts_are_mondays_ending_with_current_week() -> None:
    trend = compute_trend([], NOW, 4)

    assert [week.week_start for week in trend.weeks] == [
        date(2026, 10, 26),
        date(2026, 11, 2),
        date(2026, 11, 9),
        date(2026, 11, 16),
    ]
    assert all(week.new == week.closed == week.open_at_end == 0 for week in trend.weeks)
    assert trend.open_by_severity_now == {severity: 0 for severity in Severity}


def test_counts_new_and_closed_per_week() -> None:
    finding = make_finding(
        status=FindingStatus.FIXED,
        first_seen_at=datetime(2026, 11, 3, 10, tzinfo=UTC),
        closed_at=datetime(2026, 11, 17, 10, tzinfo=UTC),
    )

    trend = compute_trend([finding], NOW, 4)

    assert [week.new for week in trend.weeks] == [0, 1, 0, 0]
    assert [week.closed for week in trend.weeks] == [0, 0, 0, 1]
    assert [week.open_at_end for week in trend.weeks] == [0, 1, 1, 0]


def test_first_seen_exactly_at_range_start_counts_as_new() -> None:
    finding = make_finding(first_seen_at=datetime(2026, 10, 26, tzinfo=UTC))

    trend = compute_trend([finding], NOW, 4)

    assert trend.weeks[0].new == 1
    assert trend.open_at_start == 0


def test_finding_before_range_is_baseline() -> None:
    finding = make_finding(first_seen_at=NOW - timedelta(weeks=53))

    trend = compute_trend([finding], NOW, 4)

    assert trend.open_at_start == 1
    assert trend.new_total == 0


def test_closed_before_range_is_not_counted() -> None:
    finding = make_finding(
        status=FindingStatus.FIXED,
        first_seen_at=NOW - timedelta(weeks=53),
        closed_at=NOW - timedelta(weeks=20),
    )

    trend = compute_trend([finding], NOW, 4)

    assert trend.open_at_start == 0
    assert trend.closed_total == 0


def test_closed_before_first_seen_counts_nowhere() -> None:
    finding = make_finding(
        status=FindingStatus.FIXED,
        first_seen_at=datetime(2026, 11, 10, tzinfo=UTC),
        closed_at=datetime(2026, 11, 5, tzinfo=UTC),
    )
    baseline_finding = make_finding(
        status=FindingStatus.FIXED,
        first_seen_at=datetime(2026, 11, 3, tzinfo=UTC),
        closed_at=datetime(2026, 10, 1, tzinfo=UTC),
    )

    trend = compute_trend([finding, baseline_finding], NOW, 4)

    assert trend.open_at_start == 0
    assert trend.new_total == 0
    assert trend.closed_total == 0
    assert all(week.open_at_end == 0 for week in trend.weeks)


def test_finding_without_first_seen_is_skipped() -> None:
    trend = compute_trend([make_finding(first_seen_at=None)], NOW, 4)

    assert trend.open_at_start == 0
    assert all(week.open_at_end == 0 for week in trend.weeks)


def test_reopened_finding_counts_as_open() -> None:
    finding = make_finding(
        status=FindingStatus.OPEN,
        first_seen_at=NOW - timedelta(weeks=20),
        closed_at=None,
    )

    trend = compute_trend([finding], NOW, 4)

    assert trend.weeks[-1].open_at_end == 1


def test_last_week_open_matches_now_counts() -> None:
    long_ago = NOW - timedelta(weeks=30)
    findings = [
        make_finding(FindingStatus.OPEN, first_seen_at=long_ago),
        make_finding(FindingStatus.IN_PROGRESS, first_seen_at=datetime(2026, 11, 18, tzinfo=UTC)),
        make_finding(FindingStatus.IN_PROGRESS, first_seen_at=long_ago),
        make_finding(
            FindingStatus.FIXED, first_seen_at=long_ago, closed_at=NOW - timedelta(days=2)
        ),
    ]

    trend = compute_trend(findings, NOW, 4)

    assert trend.untouched_now == 1
    assert trend.in_progress_now == 2
    assert trend.weeks[-1].open_at_end == trend.untouched_now + trend.in_progress_now


def test_open_by_severity_counts_only_open_states() -> None:
    findings = [
        make_finding(FindingStatus.OPEN, level=Severity.KRITISCH),
        make_finding(FindingStatus.FIXED, level=Severity.KRITISCH),
        make_finding(FindingStatus.IN_PROGRESS, level=Severity.HOCH),
    ]

    trend = compute_trend(findings, NOW, 4)

    assert trend.open_by_severity_now == {
        Severity.KRITISCH: 1,
        Severity.HOCH: 1,
        Severity.MITTEL: 0,
        Severity.NIEDRIG: 0,
    }


def test_totals_sum_weeks() -> None:
    findings = [
        make_finding(
            FindingStatus.FIXED,
            first_seen_at=datetime(2026, 11, 3, tzinfo=UTC),
            closed_at=datetime(2026, 11, 10, tzinfo=UTC),
        ),
        make_finding(first_seen_at=datetime(2026, 11, 12, tzinfo=UTC)),
    ]

    trend = compute_trend(findings, NOW, 4)

    assert trend.new_total == sum(week.new for week in trend.weeks) == 2
    assert trend.closed_total == sum(week.closed for week in trend.weeks) == 1


def test_closed_by_outcome_counts_same_set_as_closed_total() -> None:
    seen = datetime(2026, 10, 1, tzinfo=UTC)
    findings = [
        make_finding(
            FindingStatus.FIXED,
            seen,
            datetime(2026, 11, 10, tzinfo=UTC),
            resolved_by=ResolutionSource.SBOM,
        ),
        make_finding(FindingStatus.ACCEPTED, seen, datetime(2026, 11, 12, tzinfo=UTC)),
        # vor dem Zeitraum erledigt
        make_finding(FindingStatus.FIXED, seen, datetime(2026, 10, 5, tzinfo=UTC)),
        # Altfund: erledigt vor Erstsichtung
        make_finding(FindingStatus.FALSE_POSITIVE, seen, datetime(2026, 9, 1, tzinfo=UTC)),
    ]

    trend = compute_trend(findings, NOW, 4)

    assert set(trend.closed_by_outcome) == set(ClosureKind)
    assert trend.closed_by_outcome[ClosureKind.FIXED_CONFIRMED] == 1
    assert trend.closed_by_outcome[ClosureKind.ACCEPTED] == 1
    assert trend.closed_by_outcome[ClosureKind.FIXED_REPORTED] == 0
    assert trend.closed_by_outcome[ClosureKind.FIXED_MANUAL] == 0
    assert trend.closed_by_outcome[ClosureKind.FALSE_POSITIVE] == 0
    assert sum(trend.closed_by_outcome.values()) == trend.closed_total
