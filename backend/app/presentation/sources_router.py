"""Router für die Quellen-Verwaltung. Enthält keine Logik.

Der API-Key wird nie zurückgegeben, nur ``hasApiKey``.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.application.source_registry import SourceRegistry
from app.application.source_use_cases import (
    ListSources,
    RemoveSourceApiKey,
    SetSourceApiKey,
    SetSourceEnabled,
    SourceView,
)
from app.domain.sources import (
    ApiKeyRequirement,
    MatchScope,
    RunStatus,
    SourceKind,
    SourceStatus,
)
from app.presentation.dependencies import UnitOfWorkDep
from app.presentation.schemas import ApiModel

router = APIRouter(prefix="/api/sources", tags=["sources"])


def get_source_registry(request: Request) -> SourceRegistry:
    registry: SourceRegistry = request.app.state.source_registry
    return registry


RegistryDep = Annotated[SourceRegistry, Depends(get_source_registry)]


class SourceResponse(ApiModel):
    key: str
    name: str
    homepage_url: str
    description: str
    kind: SourceKind
    scope: MatchScope
    api_key_requirement: ApiKeyRequirement
    api_key_hint: str
    has_api_key: bool
    enabled: bool
    status: SourceStatus
    last_run_at: datetime | None
    last_status: RunStatus | None
    last_message: str
    last_findings: int | None


class SetEnabledRequest(ApiModel):
    enabled: bool


class SetApiKeyRequest(ApiModel):
    api_key: str


def _to_response(view: SourceView) -> SourceResponse:
    descriptor, setting = view.descriptor, view.setting
    return SourceResponse(
        key=descriptor.key,
        name=descriptor.name,
        homepage_url=descriptor.homepage_url,
        description=descriptor.description,
        kind=descriptor.kind,
        scope=descriptor.scope,
        api_key_requirement=descriptor.api_key_requirement,
        api_key_hint=descriptor.api_key_hint,
        has_api_key=view.has_api_key,
        enabled=setting.enabled,
        status=view.status,
        last_run_at=setting.last_run_at,
        last_status=setting.last_status,
        last_message=setting.last_message,
        last_findings=setting.last_findings,
    )


@router.get("")
def list_sources(uow: UnitOfWorkDep, registry: RegistryDep) -> list[SourceResponse]:
    return [_to_response(view) for view in ListSources(uow, registry).execute()]


@router.patch("/{key}")
def set_enabled(
    key: str, body: SetEnabledRequest, uow: UnitOfWorkDep, registry: RegistryDep
) -> SourceResponse:
    return _to_response(SetSourceEnabled(uow, registry).execute(key, body.enabled))


@router.put("/{key}/api-key")
def set_api_key(
    key: str, body: SetApiKeyRequest, uow: UnitOfWorkDep, registry: RegistryDep
) -> SourceResponse:
    return _to_response(SetSourceApiKey(uow, registry).execute(key, body.api_key))


@router.delete("/{key}/api-key")
def remove_api_key(key: str, uow: UnitOfWorkDep, registry: RegistryDep) -> SourceResponse:
    return _to_response(RemoveSourceApiKey(uow, registry).execute(key))
