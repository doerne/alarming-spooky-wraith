from datetime import UTC, datetime

import pytest

from app.application.sbom_use_cases import (
    DeleteSbom,
    GetSbomVersion,
    ListSboms,
    ListSbomVersions,
    UploadSbomVersion,
)
from app.domain.errors import EntityNotFoundError
from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.sbom import ParsedSbom, SbomEntry
from app.domain.vulnerability import Finding, RiskScore, Severity
from tests.fakes import FIXED_NOW, FakeSbomParser, InMemoryUnitOfWork, fixed_clock

_NOW = datetime(2026, 11, 21, 9, 30, tzinfo=UTC)
_REACT = SbomEntry("react", "18.2.0", Category.LIBRARY, Ecosystem.NPM, True, None)
_LODASH = SbomEntry("lodash", "4.17.21", Category.LIBRARY, Ecosystem.NPM, False, None)


def _application(uow: InMemoryUnitOfWork, name: str = "Shop") -> int:
    application = uow.applications.add(Application(name=name))
    assert application.id is not None
    return application.id


def _upload(
    uow: InMemoryUnitOfWork, application_id: int, name: str, label: str, *entries: SbomEntry
) -> int:
    parsed = ParsedSbom(entries=entries, serial_number=None, suggested_label=None, skipped=0)
    result = UploadSbomVersion(uow, FakeSbomParser(parsed), lambda: _NOW).execute(
        application_id=application_id, name=name, label=label, document={}
    )
    assert result.sbom.id is not None
    return result.sbom.id


def test_list_sboms_returns_current_version_and_count() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    _upload(uow, application_id, "frontend", "1.0", _LODASH)
    _upload(uow, application_id, "backend", "1.0", _REACT)
    _upload(uow, application_id, "backend", "1.1", _REACT, _LODASH)
    overviews = ListSboms(uow).execute(application_id)
    assert [o.sbom.name for o in overviews] == ["backend", "frontend"]
    backend = overviews[0]
    assert backend.version_count == 2
    assert backend.current is not None
    assert backend.current.label == "1.1"


def test_list_sboms_of_unknown_application_raises() -> None:
    with pytest.raises(EntityNotFoundError):
        ListSboms(InMemoryUnitOfWork()).execute(999)


def test_sbom_of_other_application_is_not_found() -> None:
    uow = InMemoryUnitOfWork()
    owner = _application(uow)
    other = _application(uow, "Andere")
    sbom_id = _upload(uow, owner, "backend", "1.0", _REACT)
    version = uow.sbom_versions.current_for_sbom(sbom_id)
    assert version is not None
    assert version.id is not None
    with pytest.raises(EntityNotFoundError):
        ListSbomVersions(uow).execute(application_id=other, sbom_id=sbom_id)
    with pytest.raises(EntityNotFoundError):
        GetSbomVersion(uow).execute(application_id=other, sbom_id=sbom_id, version_id=version.id)
    with pytest.raises(EntityNotFoundError):
        DeleteSbom(uow, fixed_clock).execute(application_id=other, sbom_id=sbom_id)
    assert uow.sboms.get(sbom_id).name == "backend"


def test_version_of_other_sbom_is_not_found() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    backend = _upload(uow, application_id, "backend", "1.0", _REACT)
    frontend = _upload(uow, application_id, "frontend", "1.0", _LODASH)
    version = uow.sbom_versions.current_for_sbom(frontend)
    assert version is not None
    assert version.id is not None
    with pytest.raises(EntityNotFoundError):
        GetSbomVersion(uow).execute(
            application_id=application_id, sbom_id=backend, version_id=version.id
        )


def test_get_archived_version_returns_entries() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    sbom_id = _upload(uow, application_id, "backend", "1.0", _REACT, _LODASH)
    _upload(uow, application_id, "backend", "1.1", _REACT)
    versions = ListSbomVersions(uow).execute(application_id=application_id, sbom_id=sbom_id)
    archived = versions[-1]
    assert archived.id is not None
    loaded = GetSbomVersion(uow).execute(
        application_id=application_id, sbom_id=sbom_id, version_id=archived.id
    )
    assert loaded.is_current is False
    assert [entry.name for entry in loaded.entries] == ["react", "lodash"]


def test_delete_sbom_removes_components_findings_versions() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    manual = uow.components.add(
        application_id, Component("express", "4.0.0", Category.LIBRARY, Ecosystem.NPM, True)
    )
    sbom_id = _upload(uow, application_id, "backend", "1.0", _REACT)
    react = uow.components.list_for_sbom(sbom_id)[0]
    assert react.id is not None
    uow.findings.upsert(
        Finding(
            advisory_id="CVE-2024-1",
            component_id=react.id,
            application_id=application_id,
            found_version="18.2.0",
            risk=RiskScore(value=80, level=Severity.HOCH, rationale="r"),
        )
    )
    commits = uow.commits
    DeleteSbom(uow, fixed_clock).execute(application_id=application_id, sbom_id=sbom_id)
    assert uow.commits == commits + 1
    assert uow.components.list_for_application(application_id) == [manual]
    assert uow.findings.list() == []
    assert uow.sbom_versions.list_for_sbom(sbom_id) == []
    with pytest.raises(EntityNotFoundError):
        uow.sboms.get(sbom_id)


def test_delete_sbom_removes_retired_components() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    sbom_id = _upload(uow, application_id, "backend", "1.0", _REACT)
    react = uow.components.list_for_sbom(sbom_id)[0]
    assert react.id is not None
    uow.components.retire_many([react.id], 1)
    DeleteSbom(uow, fixed_clock).execute(application_id=application_id, sbom_id=sbom_id)
    assert uow.components.list_for_application(application_id) == []


def test_delete_sbom_marks_inventory_changed() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    sbom_id = _upload(uow, application_id, "backend", "1.0", _REACT)
    DeleteSbom(uow, fixed_clock).execute(application_id=application_id, sbom_id=sbom_id)
    assert uow.applications.get(application_id).inventory_changed_at == FIXED_NOW
