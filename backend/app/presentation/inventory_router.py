"""Router zur manuellen Inventar-Pflege. Enthaelt keine Logik."""

from fastapi import APIRouter, status

from app.application.inventory_use_cases import AddComponent, CreateApplication
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


@router.post("/applications", status_code=status.HTTP_201_CREATED)
def create_application(body: CreateApplicationRequest, uow: UnitOfWorkDep) -> ApplicationResponse:
    application = CreateApplication(uow).execute(name=body.name, description=body.description)
    assert application.id is not None
    return ApplicationResponse(
        id=application.id, name=application.name, description=application.description
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
        component=Component(
            name=body.name,
            version=body.version,
            category=body.category,
            ecosystem=body.ecosystem,
            direct=body.direct,
        ),
    )
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
