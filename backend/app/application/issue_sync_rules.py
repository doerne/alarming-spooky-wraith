"""Reine Regeln für den Abgleich zwischen CVE-Radar und GitHub-Issues (siehe Spec, Tabelle)."""

from collections.abc import Sequence
from enum import StrEnum

from app.domain.ports import TrackedIssue
from app.domain.vulnerability import Finding, FindingStatus, IssueState

_OPEN_STATUSES = frozenset({FindingStatus.OPEN, FindingStatus.IN_PROGRESS})
_RATED_STATUSES = frozenset({FindingStatus.ACCEPTED, FindingStatus.FALSE_POSITIVE})


class CveAggregate(StrEnum):
    """Gesamtzustand einer CVE über alle aktiven Treffer einer Anwendung."""

    OPEN = "offen"
    RATED = "bewertet"
    FIXED = "behoben"


class IssueAction(StrEnum):
    """Was der Use Case nach dem Vergleich tut."""

    NONE = "none"
    MARK_FIXED = "mark_fixed"
    MARK_ACCEPTED = "mark_accepted"
    MARK_CLOSED_EXTERNALLY_COMPLETED = "mark_closed_externally_completed"
    CLOSE_COMPLETED = "close_completed"
    CLOSE_NOT_PLANNED = "close_not_planned"
    REOPEN = "reopen"
    REOPEN_ISSUE = "reopen_issue"


def aggregate_state(active: Sequence[Finding], retired: Sequence[Finding]) -> CveAggregate:
    """Offen schlägt bewertet schlägt behoben. Nur aktive Treffer können offen/bewertet sein.

    Ausgebaute Treffer zählen nur für „behoben“. Ohne Treffer gilt „offen“ (kein Abschluss).
    """
    if any(finding.status in _OPEN_STATUSES for finding in active):
        return CveAggregate.OPEN
    if any(finding.status in _RATED_STATUSES for finding in active):
        return CveAggregate.RATED
    if any(finding.status == FindingStatus.FIXED for finding in [*active, *retired]):
        return CveAggregate.FIXED
    return CveAggregate.OPEN


def decide_issue_action(
    stored: IssueState | None,
    live: TrackedIssue,
    aggregate: CveAggregate,
    has_fix_evidence: bool,
) -> IssueAction:
    """Entscheidet die Aktion aus gespeichertem und aktuellem Issue-Zustand.

    Ein Issue ohne gespeicherten Zustand, das offen ist, verhält sich wie „unverändert offen“.
    """
    if live.is_open:
        return _open_issue_action(stored or IssueState.OPEN, aggregate, has_fix_evidence)
    return _closed_issue_action(stored, live, aggregate)


def _open_issue_action(
    previous: IssueState, aggregate: CveAggregate, has_fix_evidence: bool
) -> IssueAction:
    if previous == IssueState.CLOSED:
        return IssueAction.REOPEN if aggregate != CveAggregate.OPEN else IssueAction.NONE
    if aggregate == CveAggregate.RATED:
        return IssueAction.CLOSE_NOT_PLANNED
    if aggregate == CveAggregate.FIXED and has_fix_evidence:
        return IssueAction.CLOSE_COMPLETED
    return IssueAction.NONE


def _closed_issue_action(
    previous: IssueState | None, live: TrackedIssue, aggregate: CveAggregate
) -> IssueAction:
    if aggregate != CveAggregate.OPEN:
        return IssueAction.NONE
    if previous == IssueState.CLOSED:
        return IssueAction.REOPEN_ISSUE
    if live.not_planned:
        return IssueAction.MARK_ACCEPTED
    if previous == IssueState.OPEN:
        return IssueAction.MARK_CLOSED_EXTERNALLY_COMPLETED
    return IssueAction.MARK_FIXED
