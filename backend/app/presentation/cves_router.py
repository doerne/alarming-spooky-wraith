"""Router fuer die Funde-Uebersicht. Enthaelt keine Logik."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.application.advisory_detail import AdvisoryDetail, GetAdvisoryDetail
from app.application.list_findings import FindingFilter, ListFindings
from app.domain.inventory import Ecosystem
from app.domain.ports import AdvisoryStore
from app.domain.vulnerability import FindingStatus, Severity
from app.presentation.dependencies import UnitOfWorkDep
from app.presentation.schemas import ApiModel

router = APIRouter(prefix="/api", tags=["cves"])


class FindingResponse(ApiModel):
    advisory_id: str
    cve_id: str | None
    title: str
    application_id: int
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
    unfiltered_total: int


class FindingQuery(BaseModel):
    """Query-Parameter von GET /api/cves (snake_case, Listen wiederholt angeben)."""

    application_id: int | None = None
    application: list[int] = []
    severity: list[Severity] = []
    status: list[FindingStatus] = []
    ecosystem: list[Ecosystem | Literal["none"]] = []
    q: str = ""
    advisory_id: list[str] = []
    component_name: list[str] = []


def get_finding_filter(params: Annotated[FindingQuery, Query()]) -> FindingFilter:
    """Query-Parameter → FindingFilter; unbekannte Werte lehnt FastAPI mit 422 ab."""
    return FindingFilter(
        application_id=params.application_id,
        application_ids=frozenset(params.application),
        severities=frozenset(params.severity),
        statuses=frozenset(params.status),
        ecosystems=frozenset(str(value) for value in params.ecosystem),
        query=params.q,
        advisory_ids=frozenset(params.advisory_id),
        component_names=frozenset(params.component_name),
    )


FindingFilterDep = Annotated[FindingFilter, Depends(get_finding_filter)]


@router.get("/cves")
def list_cves(uow: UnitOfWorkDep, finding_filter: FindingFilterDep) -> FindingsPage:
    result = ListFindings(uow).execute(finding_filter)
    items = [
        FindingResponse(
            advisory_id=view.advisory_id,
            cve_id=view.cve_id,
            title=view.title,
            application_id=view.application_id,
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
        for view in result.items
    ]
    return FindingsPage(items=items, total=len(items), unfiltered_total=result.unfiltered_total)


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
    found_version: str
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
