"""Router fuer die Funde-Uebersicht. Enthaelt keine Logik."""

from fastapi import APIRouter

from app.application.list_findings import ListFindings
from app.domain.vulnerability import FindingStatus, Severity
from app.presentation.dependencies import UnitOfWorkDep
from app.presentation.schemas import ApiModel

router = APIRouter(prefix="/api", tags=["cves"])


class FindingResponse(ApiModel):
    advisory_id: str
    cve_id: str | None
    title: str
    application_name: str
    component_name: str
    component_version: str
    ecosystem: str | None
    risk_score: int
    risk_level: Severity
    fix_version: str | None
    status: FindingStatus


class FindingsPage(ApiModel):
    items: list[FindingResponse]
    total: int


@router.get("/cves")
def list_cves(uow: UnitOfWorkDep) -> FindingsPage:
    views = ListFindings(uow).execute()
    items = [
        FindingResponse(
            advisory_id=view.advisory_id,
            cve_id=view.cve_id,
            title=view.title,
            application_name=view.application_name,
            component_name=view.component_name,
            component_version=view.component_version,
            ecosystem=view.ecosystem,
            risk_score=view.risk_score,
            risk_level=view.risk_level,
            fix_version=view.fix_version,
            status=view.status,
        )
        for view in views
    ]
    return FindingsPage(items=items, total=len(items))
