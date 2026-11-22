"""Use Case: Wochenverlauf der Funde, optional für eine Anwendung."""

from collections.abc import Callable
from datetime import datetime

from app.application.unit_of_work import UnitOfWork
from app.domain.finding_trend import FindingTrend, compute_trend


class GetFindingTrend:
    def __init__(self, uow: UnitOfWork, clock: Callable[[], datetime]) -> None:
        self._uow = uow
        self._clock = clock

    def execute(self, weeks: int, application_id: int | None = None) -> FindingTrend:
        findings = self._uow.findings.list()
        if application_id is not None:
            self._uow.applications.get(application_id)  # EntityNotFoundError
            findings = [f for f in findings if f.application_id == application_id]
        return compute_trend(findings, self._clock(), weeks)
