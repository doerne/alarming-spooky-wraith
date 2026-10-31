from app.application.inventory_use_cases import (
    AddComponent,
    CreateApplication,
    ListApplications,
)
from app.domain.inventory import Category, Component, Ecosystem
from tests.fakes import InMemoryUnitOfWork


def _npm_component() -> Component:
    return Component(
        name="react",
        version="18.2.0",
        category=Category.LIBRARY,
        ecosystem=Ecosystem.NPM,
        direct=True,
    )


def test_create_application_assigns_id_and_commits() -> None:
    uow = InMemoryUnitOfWork()
    application = CreateApplication(uow).execute(name="Shop")
    assert application.id is not None
    assert uow.commits == 1
    assert ListApplications(uow).execute()[0].name == "Shop"


def test_add_component_links_to_application() -> None:
    uow = InMemoryUnitOfWork()
    application = CreateApplication(uow).execute(name="Shop")
    assert application.id is not None
    component = AddComponent(uow).execute(application_id=application.id, component=_npm_component())
    assert component.id is not None
    assert uow.components.list_all()[0].name == "react"
