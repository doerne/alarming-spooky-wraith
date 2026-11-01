"""Router fuer die Funde-Uebersicht. Enthaelt keine Logik."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.advisory_detail import AdvisoryDetail, GetAdvisoryDetail
from app.application.list_findings import ListFindings
from app.domain.ports import AdvisoryStore
from app.domain.vulnerability import FindingStatus, Severity
from app.presentation.dependencies import UnitOfWorkDep
from app.presentation.schemas import ApiModel

router = APIRouter(prefix="/api", tags=["cves"])


class FindingResponse(ApiModel):
    advisory_id: str
    cve_id: str | None
    title: str
    application_name: str
    component_id: int
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
def list_cves(uow: UnitOfWorkDep, application_id: int | None = None) -> FindingsPage:
    views = ListFindings(uow).execute(application_id)
    items = [
        FindingResponse(
            advisory_id=view.advisory_id,
            cve_id=view.cve_id,
            title=view.title,
            application_name=view.application_name,
            component_id=view.component_id,
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


def get_advisory_store(request: Request) -> AdvisoryStore:
    store: AdvisoryStore = request.app.state.advisory_store
    return store


StoreDep = Annotated[AdvisoryStore, Depends(get_advisory_store)]


class SourceLinkResponse(ApiModel):
    source_key: str
    url: str


class AffectedFindingResponse(ApiModel):
    application_name: str
    component_id: int
    component_name: str
    component_version: str
    ecosystem: str | None
    risk_score: int
    risk_level: Severity
    status: FindingStatus


class CveDetailResponse(ApiModel):
    advisory_id: str
    cve_id: str | None
    title: str
    cvss_base: float | None
    fix_version: str | None
    risk_score: int
    risk_level: Severity
    description: str
    rationale: str
    references: list[str]
    sources: list[SourceLinkResponse]
    findings: list[AffectedFindingResponse]


def _to_detail_response(detail: AdvisoryDetail) -> CveDetailResponse:
    return CveDetailResponse(
        advisory_id=detail.advisory_id,
        cve_id=detail.cve_id,
        title=detail.title,
        cvss_base=detail.cvss_base,
        fix_version=detail.fix_version,
        risk_score=detail.risk_score,
        risk_level=detail.risk_level,
        description=detail.description,
        rationale=detail.rationale,
        references=detail.references,
        sources=[SourceLinkResponse(source_key=s.source_key, url=s.url) for s in detail.sources],
        findings=[AffectedFindingResponse(**finding.__dict__) for finding in detail.findings],
    )


@router.get("/cves/{advisory_id}")
def get_cve(advisory_id: str, uow: UnitOfWorkDep, store: StoreDep) -> CveDetailResponse:
    return _to_detail_response(GetAdvisoryDetail(uow, store).execute(advisory_id))
