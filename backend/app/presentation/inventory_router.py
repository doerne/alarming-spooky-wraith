"""Router zur manuellen Inventar-Pflege. Enthaelt keine Logik."""

from fastapi import APIRouter, status

from app.application.inventory_use_cases import (
    AddComponent,
    CreateApplication,
    GetApplication,
    ListApplications,
    UpdateComponent,
)
from app.domain.inventory import Category, Component, Ecosystem
from app.presentation.dependencies import UnitOfWorkDep
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


class ApplicationDetailResponse(ApiModel):
    id: int
    name: str
    description: str
    components: list[ComponentResponse]


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


@router.get("/applications/{application_id}")
def get_application(application_id: int, uow: UnitOfWorkDep) -> ApplicationDetailResponse:
    application = GetApplication(uow).execute(application_id)
    assert application.id is not None
    return ApplicationDetailResponse(
        id=application.id,
        name=application.name,
        description=application.description,
        components=[_to_component_response(component) for component in application.components],
    )


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
