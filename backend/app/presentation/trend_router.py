"""Router für den Wochenverlauf der Funde. Enthält keine Logik."""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.application.finding_trend import GetFindingTrend
from app.domain.finding_trend import FindingTrend
from app.domain.vulnerability import Severity
from app.presentation.dependencies import ClockDep, UnitOfWorkDep
from app.presentation.schemas import ApiModel

router = APIRouter(prefix="/api", tags=["findings"])

# Muss mit TREND_WEEK_OPTIONS / DEFAULT_TREND_WEEKS der Domain übereinstimmen (Test).
TrendWeeks = Literal[4, 12, 26, 52]
DEFAULT_WEEKS: TrendWeeks = 12


class TrendWeekResponse(ApiModel):
    week_start: date
    new: int
    closed: int
    open_at_end: int


class FindingTrendResponse(ApiModel):
    weeks: list[TrendWeekResponse]
    open_at_start: int
    new_total: int
    closed_total: int
    untouched_now: int
    in_progress_now: int
    open_by_severity_now: dict[Severity, int]


def _to_response(trend: FindingTrend) -> FindingTrendResponse:
    return FindingTrendResponse(
        weeks=[
            TrendWeekResponse(
                week_start=week.week_start,
                new=week.new,
                closed=week.closed,
                open_at_end=week.open_at_end,
            )
            for week in trend.weeks
        ],
        open_at_start=trend.open_at_start,
        new_total=trend.new_total,
        closed_total=trend.closed_total,
        untouched_now=trend.untouched_now,
        in_progress_now=trend.in_progress_now,
        open_by_severity_now=trend.open_by_severity_now,
    )


@router.get("/findings/trend")
def get_finding_trend(
    uow: UnitOfWorkDep,
    clock: ClockDep,
    weeks: TrendWeeks = DEFAULT_WEEKS,
    application_id: Annotated[int | None, Query(alias="applicationId")] = None,
) -> FindingTrendResponse:
    return _to_response(GetFindingTrend(uow, clock).execute(weeks, application_id))
