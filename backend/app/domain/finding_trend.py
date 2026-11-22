"""Wochenverlauf neuer, erledigter und offener Funde (reine Berechnung)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from app.domain.remediation import ClosureKind, closure_kind_of
from app.domain.vulnerability import Finding, FindingStatus, Severity, is_closed

TREND_WEEK_OPTIONS: tuple[int, ...] = (4, 12, 26, 52)
DEFAULT_TREND_WEEKS = 12
_ONE_WEEK = timedelta(weeks=1)


@dataclass(frozen=True)
class TrendWeek:
    week_start: date
    new: int
    closed: int
    open_at_end: int


@dataclass(frozen=True)
class FindingTrend:
    weeks: list[TrendWeek]
    open_at_start: int
    new_total: int
    closed_total: int
    untouched_now: int
    in_progress_now: int
    open_by_severity_now: dict[Severity, int]  # immer alle vier Stufen
    closed_by_outcome: dict[ClosureKind, int]  # immer alle fünf Arten


def week_start_of(moment: datetime) -> datetime:
    """Montag 00:00 UTC der Woche, in die ``moment`` fällt."""
    monday = moment.astimezone(UTC).date() - timedelta(days=moment.astimezone(UTC).weekday())
    return datetime(monday.year, monday.month, monday.day, tzinfo=UTC)


def _is_trackable(finding: Finding) -> bool:
    """Ohne Erstsichtung oder mit Erledigung davor (Migrations-Basis) zählt ein Fund nicht."""
    if finding.first_seen_at is None:
        return False
    return finding.closed_at is None or finding.closed_at >= finding.first_seen_at


def _in_interval(moment: datetime | None, start: datetime, end: datetime) -> bool:
    return moment is not None and start <= moment < end


def _count_open_at(findings: Sequence[Finding], moment: datetime) -> int:
    """Funde, die vor ``moment`` erstmals gesehen und dann noch nicht erledigt waren."""
    return sum(
        1
        for finding in findings
        if finding.first_seen_at is not None
        and finding.first_seen_at < moment
        and (finding.closed_at is None or finding.closed_at >= moment)
    )


def _week_of(findings: Sequence[Finding], start: datetime) -> TrendWeek:
    end = start + _ONE_WEEK
    return TrendWeek(
        week_start=start.date(),
        new=sum(1 for finding in findings if _in_interval(finding.first_seen_at, start, end)),
        closed=sum(1 for finding in findings if _in_interval(finding.closed_at, start, end)),
        open_at_end=_count_open_at(findings, end),
    )


def _open_by_severity(findings: Sequence[Finding]) -> dict[Severity, int]:
    counts = {severity: 0 for severity in Severity}
    for finding in findings:
        if not is_closed(finding.status):
            counts[finding.risk.level] += 1
    return counts


def _closed_by_outcome(
    findings: Sequence[Finding], start: datetime, end: datetime
) -> dict[ClosureKind, int]:
    """Erledigte Funde im Zeitraum nach Art der Erledigung (gleiche Menge wie ``closed``)."""
    counts = {kind: 0 for kind in ClosureKind}
    for finding in findings:
        kind = closure_kind_of(finding)
        if kind is not None and _in_interval(finding.closed_at, start, end):
            counts[kind] += 1
    return counts


def _count_status(findings: Sequence[Finding], status: FindingStatus) -> int:
    return sum(1 for finding in findings if finding.status == status)


def compute_trend(findings: Sequence[Finding], now: datetime, weeks: int) -> FindingTrend:
    """Verlauf der letzten ``weeks`` ISO-Wochen; die angebrochene aktuelle Woche ist die letzte."""
    tracked = [finding for finding in findings if _is_trackable(finding)]
    range_start = week_start_of(now) - (weeks - 1) * _ONE_WEEK
    trend_weeks = [_week_of(tracked, range_start + index * _ONE_WEEK) for index in range(weeks)]
    return FindingTrend(
        weeks=trend_weeks,
        open_at_start=_count_open_at(tracked, range_start),
        new_total=sum(week.new for week in trend_weeks),
        closed_total=sum(week.closed for week in trend_weeks),
        untouched_now=_count_status(findings, FindingStatus.OPEN),
        in_progress_now=_count_status(findings, FindingStatus.IN_PROGRESS),
        open_by_severity_now=_open_by_severity(findings),
        closed_by_outcome=_closed_by_outcome(tracked, range_start, range_start + weeks * _ONE_WEEK),
    )
