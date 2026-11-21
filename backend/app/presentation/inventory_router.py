"""Router zur manuellen Inventar-Pflege. Enthaelt keine Logik."""

from datetime import datetime

from fastapi import APIRouter, status

from app.application.github_settings import GitHubSettingsChange, UpdateGitHubSettings
from app.application.inventory_use_cases import (
    AddComponent,
    CreateApplication,
    GetApplication,
    ListApplications,
    UpdateComponent,
)
from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.vulnerability import Severity
from app.presentation.dependencies import ClockDep, UnitOfWorkDep
from app.presentation.schemas import ApiModel

router = APIRouter(prefix="/api", tags=["inventory"])


class CreateApplicationRequest(ApiModel):
    name: str
    description: str = ""


class ApplicationResponse(ApiModel):
    id: int
    name: str
    description: str


class CreateComponentRequest(ApiModel):
    name: str
    version: str
    category: Category
    ecosystem: Ecosystem | None = None
    direct: bool = True


class ComponentResponse(ApiModel):
    id: int
    application_id: int
    name: str
    version: str
    category: Category
    ecosystem: Ecosystem | None
    direct: bool
    sbom_id: int | None
    checked: bool


class ApplicationDetailResponse(ApiModel):
    id: int
    name: str
    description: str
    components: list[ComponentResponse]
    github_repository: str | None
    auto_issue_min_level: Severity | None
    github_synced_at: datetime | None
    github_sync_message: str


class UpdateApplicationRequest(ApiModel):
    """Nur übergebene Felder ändern etwas; ``null`` entfernt den Wert."""

    github_repository: str | None = None
    auto_issue_min_level: Severity | None = None


def _component_from_request(body: CreateComponentRequest) -> Component:
    return Component(
        name=body.name,
        version=body.version,
        category=body.category,
        ecosystem=body.ecosystem,
        direct=body.direct,
    )


def _to_component_response(component: Component) -> ComponentResponse:
    assert component.id is not None
    assert component.application_id is not None
    return ComponentResponse(
        id=component.id,
        application_id=component.application_id,
        name=component.name,
        version=component.version,
        category=component.category,
        ecosystem=component.ecosystem,
        direct=component.direct,
        sbom_id=component.sbom_id,
        checked=component.checked,
    )


@router.post("/applications", status_code=status.HTTP_201_CREATED)
def create_application(body: CreateApplicationRequest, uow: UnitOfWorkDep) -> ApplicationResponse:
    application = CreateApplication(uow).execute(name=body.name, description=body.description)
    assert application.id is not None
    return ApplicationResponse(
        id=application.id, name=application.name, description=application.description
    )


@router.get("/applications")
def list_applications(uow: UnitOfWorkDep) -> list[ApplicationResponse]:
    applications = ListApplications(uow).execute()
    return [
        ApplicationResponse(id=app.id, name=app.name, description=app.description)
        for app in applications
        if app.id is not None
    ]


def _to_detail_response(application: Application) -> ApplicationDetailResponse:
    assert application.id is not None
    return ApplicationDetailResponse(
        id=application.id,
        name=application.name,
        description=application.description,
        components=[_to_component_response(component) for component in application.components],
        github_repository=application.github_repository,
        auto_issue_min_level=application.auto_issue_min_level,
        github_synced_at=application.github_synced_at,
        github_sync_message=application.github_sync_message,
    )


@router.get("/applications/{application_id}")
def get_application(application_id: int, uow: UnitOfWorkDep) -> ApplicationDetailResponse:
    return _to_detail_response(GetApplication(uow).execute(application_id))


@router.patch("/applications/{application_id}")
def update_application(
    application_id: int, body: UpdateApplicationRequest, uow: UnitOfWorkDep, clock: ClockDep
) -> ApplicationDetailResponse:
    fields = body.model_fields_set
    change = GitHubSettingsChange(
        repository=body.github_repository,
        min_level=body.auto_issue_min_level,
        set_repository="github_repository" in fields,
        set_min_level="auto_issue_min_level" in fields,
    )
    UpdateGitHubSettings(uow, clock).execute(application_id, change)
    return _to_detail_response(GetApplication(uow).execute(application_id))


@router.post(
    "/applications/{application_id}/components",
    status_code=status.HTTP_201_CREATED,
)
def add_component(
    application_id: int, body: CreateComponentRequest, uow: UnitOfWorkDep
) -> ComponentResponse:
    component = AddComponent(uow).execute(
        application_id=application_id,
        component=_component_from_request(body),
    )
    return _to_component_response(component)


@router.put("/applications/{application_id}/components/{component_id}")
def update_component(
    application_id: int,
    component_id: int,
    body: CreateComponentRequest,
    uow: UnitOfWorkDep,
) -> ComponentResponse:
    component = UpdateComponent(uow).execute(
        application_id=application_id,
        component_id=component_id,
        component=_component_from_request(body),
    )
    return _to_component_response(component)
