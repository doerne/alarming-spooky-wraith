"""Router zum Hinterlegen von SBOMs an einer Anwendung. Enthaelt keine Logik.

Den Parser setzt der Composition Root (app/main.py) als ``app.state.sbom_parser``.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import Field

from app.application.sbom_use_cases import (
    DeleteSbom,
    GetSbomVersion,
    ListSboms,
    ListSbomVersions,
    SbomOverview,
    UploadSbomVersion,
)
from app.domain.inventory import Category, Ecosystem
from app.domain.ports import SbomParser
from app.domain.sbom import SBOM_LABEL_MAX_LENGTH, SBOM_NAME_MAX_LENGTH, SbomEntry, SbomVersion
from app.presentation.dependencies import ClockDep, UnitOfWorkDep
from app.presentation.schemas import ApiModel

router = APIRouter(prefix="/api/applications/{application_id}/sboms", tags=["sbom"])


def get_sbom_parser(request: Request) -> SbomParser:
    parser: SbomParser = request.app.state.sbom_parser
    return parser


ParserDep = Annotated[SbomParser, Depends(get_sbom_parser)]


class UploadSbomRequest(ApiModel):
    name: str = Field(min_length=1, max_length=SBOM_NAME_MAX_LENGTH)
    label: str | None = Field(default=None, max_length=SBOM_LABEL_MAX_LENGTH)
    document: dict[str, object]


class SbomVersionSummaryResponse(ApiModel):
    id: int
    label: str
    uploaded_at: datetime
    is_current: bool
    component_count: int
    unchecked_count: int


class SbomEntryResponse(ApiModel):
    name: str
    version: str
    category: Category
    ecosystem: Ecosystem | None
    direct: bool
    purl: str | None
    checked: bool


class SbomVersionDetailResponse(SbomVersionSummaryResponse):
    components: list[SbomEntryResponse]


class SbomSummaryResponse(ApiModel):
    id: int
    name: str
    version_count: int
    current: SbomVersionSummaryResponse | None


class SbomUploadResponse(ApiModel):
    sbom_id: int
    version: SbomVersionSummaryResponse
    added: int
    removed: int
    kept: int
    unchecked: int
    skipped: int


def _version_summary(version: SbomVersion) -> SbomVersionSummaryResponse:
    assert version.id is not None
    return SbomVersionSummaryResponse(
        id=version.id,
        label=version.label,
        uploaded_at=version.uploaded_at,
        is_current=version.is_current,
        component_count=version.component_count,
        unchecked_count=version.unchecked_count,
    )


def _entry_response(entry: SbomEntry) -> SbomEntryResponse:
    return SbomEntryResponse(
        name=entry.name,
        version=entry.version,
        category=entry.category,
        ecosystem=entry.ecosystem,
        direct=entry.direct,
        purl=entry.purl,
        checked=entry.checked,
    )


def _sbom_summary(overview: SbomOverview) -> SbomSummaryResponse:
    assert overview.sbom.id is not None
    return SbomSummaryResponse(
        id=overview.sbom.id,
        name=overview.sbom.name,
        version_count=overview.version_count,
        current=_version_summary(overview.current) if overview.current else None,
    )


@router.get("")
def list_sboms(application_id: int, uow: UnitOfWorkDep) -> list[SbomSummaryResponse]:
    return [_sbom_summary(overview) for overview in ListSboms(uow).execute(application_id)]


@router.post("/versions", status_code=status.HTTP_201_CREATED)
def upload_sbom_version(
    application_id: int,
    body: UploadSbomRequest,
    uow: UnitOfWorkDep,
    parser: ParserDep,
    clock: ClockDep,
) -> SbomUploadResponse:
    result = UploadSbomVersion(uow, parser, clock).execute(
        application_id=application_id, name=body.name, label=body.label, document=body.document
    )
    assert result.sbom.id is not None
    return SbomUploadResponse(
        sbom_id=result.sbom.id,
        version=_version_summary(result.version),
        added=result.added,
        removed=result.removed,
        kept=result.kept,
        unchecked=result.unchecked,
        skipped=result.skipped,
    )


@router.get("/{sbom_id}/versions")
def list_sbom_versions(
    application_id: int, sbom_id: int, uow: UnitOfWorkDep
) -> list[SbomVersionSummaryResponse]:
    versions = ListSbomVersions(uow).execute(application_id=application_id, sbom_id=sbom_id)
    return [_version_summary(version) for version in versions]


@router.get("/{sbom_id}/versions/{version_id}")
def get_sbom_version(
    application_id: int, sbom_id: int, version_id: int, uow: UnitOfWorkDep
) -> SbomVersionDetailResponse:
    version = GetSbomVersion(uow).execute(
        application_id=application_id, sbom_id=sbom_id, version_id=version_id
    )
    return SbomVersionDetailResponse(
        **_version_summary(version).model_dump(),
        components=[_entry_response(entry) for entry in version.entries],
    )


@router.delete("/{sbom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sbom(application_id: int, sbom_id: int, uow: UnitOfWorkDep) -> Response:
    DeleteSbom(uow).execute(application_id=application_id, sbom_id=sbom_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
