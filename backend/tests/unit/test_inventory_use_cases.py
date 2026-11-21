from dataclasses import replace

import pytest

from app.application.inventory_use_cases import (
    AddComponent,
    CreateApplication,
    ListApplications,
    UpdateComponent,
)
from app.domain.errors import ComponentManagedBySbomError, EntityNotFoundError
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


def test_add_component_to_missing_application_raises() -> None:
    uow = InMemoryUnitOfWork()
    with pytest.raises(EntityNotFoundError):
        AddComponent(uow).execute(application_id=999, component=_npm_component())


def test_add_component_links_to_application() -> None:
    uow = InMemoryUnitOfWork()
    application = CreateApplication(uow).execute(name="Shop")
    assert application.id is not None
    component = AddComponent(uow).execute(application_id=application.id, component=_npm_component())
    assert component.id is not None
    assert uow.components.list_all()[0].name == "react"


def test_update_sbom_component_is_rejected() -> None:
    uow = InMemoryUnitOfWork()
    application = CreateApplication(uow).execute(name="Shop")
    assert application.id is not None
    stored = uow.components.add(application.id, replace(_npm_component(), sbom_id=3))
    assert stored.id is not None
    with pytest.raises(ComponentManagedBySbomError):
        UpdateComponent(uow).execute(
            application_id=application.id, component_id=stored.id, component=_npm_component()
        )
