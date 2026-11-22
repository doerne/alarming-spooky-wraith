from dataclasses import replace
from datetime import timedelta

import pytest

from app.application.inventory_use_cases import (
    AddComponent,
    CreateApplication,
    GetApplication,
    ListApplications,
    UpdateComponent,
)
from app.domain.errors import ComponentManagedBySbomError, EntityNotFoundError
from app.domain.inventory import Category, Component, Ecosystem
from tests.fakes import FIXED_NOW, InMemoryUnitOfWork, fixed_clock


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
    application = CreateApplication(uow, fixed_clock).execute(name="Shop")
    assert application.id is not None
    assert uow.commits == 1
    assert ListApplications(uow).execute()[0].name == "Shop"


def test_add_component_to_missing_application_raises() -> None:
    uow = InMemoryUnitOfWork()
    with pytest.raises(EntityNotFoundError):
        AddComponent(uow, fixed_clock).execute(application_id=999, component=_npm_component())


def test_add_component_links_to_application() -> None:
    uow = InMemoryUnitOfWork()
    application = CreateApplication(uow, fixed_clock).execute(name="Shop")
    assert application.id is not None
    component = AddComponent(uow, fixed_clock).execute(
        application_id=application.id, component=_npm_component()
    )
    assert component.id is not None
    assert uow.components.list_all()[0].name == "react"


def test_update_sbom_component_is_rejected() -> None:
    uow = InMemoryUnitOfWork()
    application = CreateApplication(uow, fixed_clock).execute(name="Shop")
    assert application.id is not None
    stored = uow.components.add(application.id, replace(_npm_component(), sbom_id=3))
    assert stored.id is not None
    with pytest.raises(ComponentManagedBySbomError):
        UpdateComponent(uow, fixed_clock).execute(
            application_id=application.id, component_id=stored.id, component=_npm_component()
        )


def test_get_application_hides_retired_components() -> None:
    uow = InMemoryUnitOfWork()
    application = CreateApplication(uow, fixed_clock).execute(name="Shop")
    assert application.id is not None
    uow.components.add(application.id, _npm_component())
    uow.components.add(
        application.id, replace(_npm_component(), name="old", retired_in_version_id=4)
    )
    names = [c.name for c in GetApplication(uow).execute(application.id).components]
    assert names == ["react"]


def test_create_application_marks_inventory_changed() -> None:
    uow = InMemoryUnitOfWork()
    application = CreateApplication(uow, fixed_clock).execute(name="Shop")
    assert application.inventory_changed_at == FIXED_NOW


def test_component_changes_mark_inventory_changed() -> None:
    uow = InMemoryUnitOfWork()
    application = CreateApplication(uow, lambda: FIXED_NOW - timedelta(days=1)).execute(name="Shop")
    assert application.id is not None
    added = AddComponent(uow, fixed_clock).execute(
        application_id=application.id, component=_npm_component()
    )
    assert uow.applications.get(application.id).inventory_changed_at == FIXED_NOW
    later = FIXED_NOW + timedelta(hours=1)
    assert added.id is not None
    UpdateComponent(uow, lambda: later).execute(
        application_id=application.id, component_id=added.id, component=_npm_component()
    )
    assert uow.applications.get(application.id).inventory_changed_at == later
