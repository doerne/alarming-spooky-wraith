from dataclasses import replace
from datetime import timedelta

import pytest

from app.application.inventory_use_cases import (
    AddComponent,
    CreateApplication,
    DeleteApplication,
    GetApplication,
    ListApplications,
    UpdateComponent,
)
from app.domain.errors import (
    ApplicationBusyError,
    ComponentManagedBySbomError,
    EntityNotFoundError,
)
from app.domain.inventory import Category, Component, Ecosystem
from app.domain.sbom import Sbom, SbomVersion
from app.domain.vulnerability import Advisory, Finding, RiskScore, Severity
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


class _Activity:
    def __init__(self, busy: bool) -> None:
        self._busy = busy

    def is_busy(self) -> bool:
        return self._busy


def _application_with_inventory(uow: InMemoryUnitOfWork, name: str) -> int:
    application = CreateApplication(uow, fixed_clock).execute(name=name)
    assert application.id is not None
    sbom = uow.sboms.add(Sbom(application_id=application.id, name="img"))
    assert sbom.id is not None
    uow.sbom_versions.add(SbomVersion(sbom.id, "v1", FIXED_NOW, None, True, ()))
    component = uow.components.add(
        application.id,
        Component("react", "18.2.0", Category.LIBRARY, Ecosystem.NPM, True, sbom_id=sbom.id),
    )
    assert component.id is not None
    uow.findings.upsert(
        Finding(
            advisory_id="CVE-1",
            component_id=component.id,
            application_id=application.id,
            found_version="18.2.0",
            risk=RiskScore(value=50, level=Severity.MITTEL, rationale=""),
        )
    )
    return application.id


def test_delete_application_removes_only_its_own_data() -> None:
    uow = InMemoryUnitOfWork()
    uow.advisories.upsert(Advisory("CVE-1", "CVE-1", "t", "d", 5.0, None, [], "a.md"))
    doomed = _application_with_inventory(uow, "A")
    kept = _application_with_inventory(uow, "B")
    DeleteApplication(uow, _Activity(busy=False)).execute(doomed)
    assert [app.id for app in uow.applications.list()] == [kept]
    assert [c.application_id for c in uow.components.list_all()] == [kept]
    assert [f.application_id for f in uow.findings.list()] == [kept]
    assert [s.application_id for s in uow.sboms.list_for_application(doomed)] == []
    assert len(uow.sboms.list_for_application(kept)) == 1
    assert uow.advisories.find("CVE-1") is not None
    assert uow.commits >= 1


def test_delete_unknown_application_raises_not_found() -> None:
    with pytest.raises(EntityNotFoundError):
        DeleteApplication(InMemoryUnitOfWork(), _Activity(busy=False)).execute(999)


def test_delete_application_is_refused_while_busy() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application_with_inventory(uow, "A")
    with pytest.raises(ApplicationBusyError):
        DeleteApplication(uow, _Activity(busy=True)).execute(application_id)
    assert len(uow.applications.list()) == 1
    assert len(uow.components.list_all()) == 1
    assert len(uow.findings.list()) == 1
