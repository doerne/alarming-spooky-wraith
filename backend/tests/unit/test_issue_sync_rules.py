import pytest

from app.application.issue_sync_rules import (
    CveAggregate,
    IssueAction,
    aggregate_state,
    decide_issue_action,
)
from app.domain.ports import TrackedIssue
from app.domain.vulnerability import Finding, FindingStatus, IssueState, RiskScore, Severity

OPEN_ISSUE = TrackedIssue(number=7, url="u", is_open=True)
COMPLETED = TrackedIssue(number=7, url="u", is_open=False)
NOT_PLANNED = TrackedIssue(number=7, url="u", is_open=False, not_planned=True)


def _finding(status: FindingStatus) -> Finding:
    return Finding(
        advisory_id="CVE-2024-1",
        component_id=1,
        application_id=1,
        found_version="1.0",
        risk=RiskScore(value=50, level=Severity.MITTEL, rationale="r"),
        status=status,
    )


@pytest.mark.parametrize(
    ("stored", "live", "aggregate", "has_fix", "expected"),
    [
        (None, COMPLETED, CveAggregate.OPEN, False, IssueAction.MARK_FIXED),
        (None, NOT_PLANNED, CveAggregate.OPEN, False, IssueAction.MARK_ACCEPTED),
        (None, COMPLETED, CveAggregate.RATED, False, IssueAction.NONE),
        (None, OPEN_ISSUE, CveAggregate.OPEN, False, IssueAction.NONE),
        (None, OPEN_ISSUE, CveAggregate.FIXED, True, IssueAction.CLOSE_COMPLETED),
        (
            IssueState.OPEN,
            COMPLETED,
            CveAggregate.OPEN,
            False,
            IssueAction.MARK_CLOSED_EXTERNALLY_COMPLETED,
        ),
        (IssueState.OPEN, NOT_PLANNED, CveAggregate.OPEN, False, IssueAction.MARK_ACCEPTED),
        (IssueState.OPEN, COMPLETED, CveAggregate.RATED, False, IssueAction.NONE),
        (IssueState.OPEN, OPEN_ISSUE, CveAggregate.FIXED, True, IssueAction.CLOSE_COMPLETED),
        (IssueState.OPEN, OPEN_ISSUE, CveAggregate.FIXED, False, IssueAction.NONE),
        (IssueState.OPEN, OPEN_ISSUE, CveAggregate.RATED, False, IssueAction.CLOSE_NOT_PLANNED),
        (IssueState.OPEN, OPEN_ISSUE, CveAggregate.OPEN, False, IssueAction.NONE),
        (IssueState.CLOSED, OPEN_ISSUE, CveAggregate.FIXED, False, IssueAction.REOPEN),
        (IssueState.CLOSED, OPEN_ISSUE, CveAggregate.RATED, False, IssueAction.REOPEN),
        (IssueState.CLOSED, OPEN_ISSUE, CveAggregate.OPEN, False, IssueAction.NONE),
        (IssueState.CLOSED, COMPLETED, CveAggregate.OPEN, False, IssueAction.REOPEN_ISSUE),
        (IssueState.CLOSED, COMPLETED, CveAggregate.FIXED, False, IssueAction.NONE),
    ],
)
def test_issue_action_follows_design_table(
    stored: IssueState | None,
    live: TrackedIssue,
    aggregate: CveAggregate,
    has_fix: bool,
    expected: IssueAction,
) -> None:
    assert decide_issue_action(stored, live, aggregate, has_fix) == expected


def test_open_findings_make_cve_open_even_with_fixed_ones() -> None:
    active = [_finding(FindingStatus.FIXED), _finding(FindingStatus.IN_PROGRESS)]
    assert aggregate_state(active, []) == CveAggregate.OPEN


def test_rated_beats_fixed_among_active() -> None:
    active = [_finding(FindingStatus.FALSE_POSITIVE), _finding(FindingStatus.FIXED)]
    assert aggregate_state(active, []) == CveAggregate.RATED


def test_retired_fixed_counts_as_fixed_but_retired_open_does_not_count_as_open() -> None:
    assert aggregate_state([], [_finding(FindingStatus.FIXED)]) == CveAggregate.FIXED
    active = [_finding(FindingStatus.FIXED)]
    assert aggregate_state(active, [_finding(FindingStatus.OPEN)]) == CveAggregate.FIXED
