"""Router fuer die Funde-Uebersicht. Enthaelt keine Logik."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, Field, model_validator

from app.application.advisory_detail import AdvisoryDetail, GetAdvisoryDetail
from app.application.finding_report import ProgressReport, ReportFindingProgress
from app.application.issue_export import ExportApplicationIssues
from app.application.list_findings import FindingFilter, ListFindings
from app.domain.inventory import Ecosystem
from app.domain.ports import AdvisoryStore
from app.domain.vulnerability import (
    ISSUE_URL_MAX_LENGTH,
    REPORT_COMMENT_MAX_LENGTH,
    FindingStatus,
    Severity,
)
from app.presentation.dependencies import ClockDep, UnitOfWorkDep
from app.presentation.issue_export_markdown import export_filename, render_issue_export
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
    issue_url: str | None = None


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
            issue_url=view.issue_url,
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


MARKDOWN_MEDIA_TYPE = "text/markdown; charset=utf-8"


@router.get("/applications/{application_id}/cves/export")
def export_application_issues(
    application_id: int, uow: UnitOfWorkDep, store: StoreDep, clock: ClockDep
) -> Response:
    """Offene CVEs als Markdown-Vorlagen für GitHub-Issues (Download)."""
    export = ExportApplicationIssues(uow, store, clock).execute(application_id)
    return Response(
        content=render_issue_export(export),
        media_type=MARKDOWN_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{export_filename(export)}"'},
    )


# Nur http(s); keine Leer-/Steuerzeichen und keine Zeichen, die in Markdown Links,
# Code oder HTML bilden (die URL landet in Issue-Texten).
_ISSUE_URL_PATTERN = r"^https?://[^\x00-\x20\x7f<>\"'`()\[\]]+$"


class ProgressReportRequest(ApiModel):
    status: FindingStatus | None = None
    issue_url: str | None = Field(
        default=None, max_length=ISSUE_URL_MAX_LENGTH, pattern=_ISSUE_URL_PATTERN
    )
    comment: str | None = Field(default=None, max_length=REPORT_COMMENT_MAX_LENGTH)

    @model_validator(mode="after")
    def _needs_one_field(self) -> "ProgressReportRequest":
        if self.status is None and self.issue_url is None and not self.comment:
            raise ValueError("status, issueUrl oder comment angeben")
        return self


class ProgressReportResponse(ApiModel):
    advisory_id: str
    updated: int


@router.patch("/applications/{application_id}/cves/{advisory_id}")
def report_progress(
    application_id: int,
    advisory_id: str,
    body: ProgressReportRequest,
    uow: UnitOfWorkDep,
    clock: ClockDep,
) -> ProgressReportResponse:
    """Rückmeldung eines Agenten (Issue angelegt, in Arbeit, behoben …)."""
    canonical_id, updated = ReportFindingProgress(uow, clock).execute(
        application_id=application_id,
        advisory_id=advisory_id,
        report=ProgressReport(status=body.status, issue_url=body.issue_url, comment=body.comment),
    )
    return ProgressReportResponse(advisory_id=canonical_id, updated=updated)
