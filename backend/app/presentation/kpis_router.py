"""Router für die Behebungs-Kennzahlen (Fristen, Update-Ziele). Enthält keine Logik."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.application.remediation_kpis import GetRemediationKpis, RemediationKpis
from app.domain.ports import VersionComparator
from app.domain.vulnerability import Severity
from app.presentation.dependencies import ClockDep, UnitOfWorkDep
from app.presentation.schemas import ApiModel

router = APIRouter(prefix="/api", tags=["findings"])


def get_version_comparator(request: Request) -> VersionComparator:
    comparator: VersionComparator = request.app.state.version_comparator
    return comparator


VersionComparatorDep = Annotated[VersionComparator, Depends(get_version_comparator)]


class DeadlinesResponse(ApiModel):
    overdue: int
    due_soon: int
    overdue_by_severity: dict[Severity, int]
    next_due_at: datetime | None


class UpdateTargetResponse(ApiModel):
    package_name: str
    ecosystem: str | None
    target_version: str
    findings: int
    applications: int


class UpdatesResponse(ApiModel):
    targets: list[UpdateTargetResponse]
    fixable_open: int
    open_total: int
    more_packages: int


class RemediationKpisResponse(ApiModel):
    deadlines: DeadlinesResponse
    updates: UpdatesResponse


def _to_response(kpis: RemediationKpis) -> RemediationKpisResponse:
    deadlines, updates = kpis.deadlines, kpis.updates
    return RemediationKpisResponse(
        deadlines=DeadlinesResponse(
            overdue=deadlines.overdue,
            due_soon=deadlines.due_soon,
            overdue_by_severity=deadlines.overdue_by_severity,
            next_due_at=deadlines.next_due_at,
        ),
        updates=UpdatesResponse(
            targets=[
                UpdateTargetResponse(
                    package_name=target.package_name,
                    ecosystem=target.ecosystem,
                    target_version=target.target_version,
                    findings=target.findings,
                    applications=target.applications,
                )
                for target in updates.targets
            ],
            fixable_open=updates.fixable_open,
            open_total=updates.open_total,
            more_packages=updates.more_packages,
        ),
    )


@router.get("/findings/kpis")
def get_remediation_kpis(
    uow: UnitOfWorkDep,
    clock: ClockDep,
    versions: VersionComparatorDep,
    application_id: Annotated[int | None, Query(alias="applicationId")] = None,
) -> RemediationKpisResponse:
    return _to_response(GetRemediationKpis(uow, clock, versions).execute(application_id))
