from datetime import UTC, datetime, timedelta

from app.domain.remediation import (
    DEADLINE_DAYS,
    ClosureKind,
    OpenItem,
    UpdateTarget,
    closure_kind_of,
    compute_deadlines,
    compute_update_targets,
    due_at,
)
from app.domain.vulnerability import Finding, FindingStatus, ResolutionSource, RiskScore, Severity
from tests.fakes import TupleVersionComparator

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


VERSIONS = TupleVersionComparator()


def item(
    package: str = "lodash",
    found: str = "4.17.0",
    fixed: str | None = "4.17.21",
    application_id: int = 1,
    ecosystem: str | None = "npm",
) -> OpenItem:
    return OpenItem(package, ecosystem, found, fixed, application_id)


def test_groups_by_package_and_takes_highest_valid_fix() -> None:
    summary = compute_update_targets(
        [item(fixed="4.17.12"), item(fixed="4.17.21", application_id=2), item(fixed="4.17.19")],
        VERSIONS,
    )
    assert summary.targets == [UpdateTarget("lodash", "npm", "4.17.21", 3, 2)]
    assert (summary.fixable_open, summary.open_total, summary.more_packages) == (3, 3, 0)


def test_fix_not_newer_or_missing_is_not_fixable() -> None:
    summary = compute_update_targets(
        [item(found="5.0.0", fixed="4.17.21"), item(fixed=None), item(fixed="kaputt")], VERSIONS
    )
    assert summary.targets == []
    assert (summary.fixable_open, summary.open_total) == (0, 3)


def test_same_name_in_other_ecosystem_is_separate_package() -> None:
    summary = compute_update_targets(
        [item(), item(ecosystem="PyPI", found="1.0", fixed="2.0")], VERSIONS
    )
    assert len(summary.targets) == 2


def test_sorted_by_findings_then_name_and_limited() -> None:
    items = [item(package=f"p{index}") for index in range(6)] + [
        item(package="z"),
        item(package="z"),
    ]
    summary = compute_update_targets(items, VERSIONS, limit=5)
    assert [target.package_name for target in summary.targets] == ["z", "p0", "p1", "p2", "p3"]
    assert summary.more_packages == 2


def test_same_name_same_count_in_two_ecosystems_has_fixed_order() -> None:
    first = compute_update_targets(
        [item(package="x", ecosystem="PyPI", found="1.0", fixed="2.0"), item(package="x")],
        VERSIONS,
    )
    second = compute_update_targets(
        [item(package="x"), item(package="x", ecosystem="PyPI", found="1.0", fixed="2.0")],
        VERSIONS,
    )
    expected = sorted(["npm", "PyPI"])
    assert [t.ecosystem for t in first.targets] == expected
    assert [t.ecosystem for t in second.targets] == expected


def test_applications_are_counted_by_id_not_name() -> None:
    summary = compute_update_targets(
        [item(application_id=1), item(application_id=1), item(application_id=2)], VERSIONS
    )
    assert summary.targets[0].applications == 2


def test_fixed_version_equal_to_found_is_not_fixable() -> None:
    summary = compute_update_targets([item(found="4.17.21", fixed="4.17.21")], VERSIONS)
    assert summary.targets == []
    assert summary.fixable_open == 0


def test_empty_items_give_empty_summary() -> None:
    summary = compute_update_targets([], VERSIONS)
    assert summary.targets == []
    assert (summary.fixable_open, summary.open_total, summary.more_packages) == (0, 0, 0)


def test_due_exactly_in_seven_days_counts_as_due_soon() -> None:
    first_seen = NOW + timedelta(days=7) - timedelta(days=DEADLINE_DAYS[Severity.KRITISCH])
    summary = compute_deadlines(
        [make_finding(first_seen_at=first_seen, level=Severity.KRITISCH)], NOW
    )
    assert (summary.overdue, summary.due_soon) == (0, 1)
