from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.domain.errors import EntityNotFoundError
from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.sbom import Sbom, SbomEntry, SbomVersion
from app.domain.sources import RunStatus, SourceSetting
from app.domain.vulnerability import (
    Advisory,
    Finding,
    FindingStatus,
    IssueState,
    RiskScore,
    Severity,
)
from app.infrastructure import models  # noqa: F401  (Modelle registrieren)
from app.infrastructure.database import Base
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def uow() -> SqlAlchemyUnitOfWork:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return SqlAlchemyUnitOfWork(Session(engine))


def _advisory() -> Advisory:
    return Advisory(
        advisory_id="CVE-2024-1",
        cve_id="CVE-2024-1",
        title="t",
        description="d",
        cvss_base=9.8,
        fixed_version="18.2.1",
        references=[],
        okf_path="advisories/CVE-2024-1.md",
    )


def _finding(component_id: int, application_id: int) -> Finding:
    return Finding(
        advisory_id="CVE-2024-1",
        component_id=component_id,
        application_id=application_id,
        found_version="18.2.0",
        risk=RiskScore(value=98, level=Severity.KRITISCH, rationale="r"),
    )


def test_roundtrip_and_finding_upsert_is_idempotent(uow: SqlAlchemyUnitOfWork) -> None:
    application = uow.applications.add(Application(name="Shop"))
    assert application.id is not None
    component = uow.components.add(
        application.id,
        Component(
            name="react",
            version="18.2.0",
            category=Category.LIBRARY,
            ecosystem=Ecosystem.NPM,
            direct=True,
        ),
    )
    assert component.id is not None
    uow.advisories.upsert(_advisory())
    uow.findings.upsert(_finding(component.id, application.id))
    uow.findings.upsert(_finding(component.id, application.id))
    uow.commit()

    assert len(uow.findings.list()) == 1
    stored = uow.components.list_all()[0]
    assert stored.name == "react"
    assert stored.ecosystem == Ecosystem.NPM
    assert stored.application_id == application.id
    assert uow.advisories.get("CVE-2024-1").fixed_version == "18.2.1"


def test_get_missing_application_raises(uow: SqlAlchemyUnitOfWork) -> None:
    with pytest.raises(EntityNotFoundError):
        uow.applications.get(999)


def test_source_setting_roundtrip(uow: SqlAlchemyUnitOfWork) -> None:
    run_at = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    setting = SourceSetting(
        source_key="osv",
        enabled=False,
        api_key="secret",
        last_run_at=run_at,
        last_status=RunStatus.OK,
        last_message="fertig",
        last_findings=3,
    )
    uow.source_settings.save(setting)
    uow.commit()
    loaded = uow.source_settings.get("osv")
    assert loaded is not None
    assert loaded.enabled is False
    assert loaded.api_key == "secret"
    assert loaded.last_run_at is not None
    assert loaded.last_run_at.replace(tzinfo=UTC) == run_at
    assert loaded.last_status == RunStatus.OK
    assert loaded.last_message == "fertig"
    assert loaded.last_findings == 3


def test_source_setting_save_updates_existing(uow: SqlAlchemyUnitOfWork) -> None:
    uow.source_settings.save(SourceSetting(source_key="osv"))
    uow.source_settings.save(SourceSetting(source_key="osv", enabled=False))
    uow.commit()
    settings = uow.source_settings.get_all()
    assert len(settings) == 1
    assert settings[0].enabled is False


def test_get_unknown_source_setting_returns_none(uow: SqlAlchemyUnitOfWork) -> None:
    assert uow.source_settings.get("unknown") is None


def test_upsert_keeps_triage_status(uow: SqlAlchemyUnitOfWork) -> None:
    application = uow.applications.add(Application(name="Shop"))
    assert application.id is not None
    component = uow.components.add(
        application.id,
        Component(
            name="react",
            version="18.2.0",
            category=Category.LIBRARY,
            ecosystem=Ecosystem.NPM,
            direct=True,
        ),
    )
    assert component.id is not None
    uow.advisories.upsert(_advisory())
    triaged = _finding(component.id, application.id)
    triaged.status = FindingStatus.FALSE_POSITIVE
    triaged.comment = "betrifft uns nicht"
    uow.findings.upsert(triaged)
    uow.commit()
    again = uow.findings.upsert(_finding(component.id, application.id))
    uow.commit()
    stored = uow.findings.list()[0]
    assert stored.status == FindingStatus.FALSE_POSITIVE
    assert stored.comment == "betrifft uns nicht"
    assert again.status == FindingStatus.FALSE_POSITIVE


def _app_with_sbom(uow: SqlAlchemyUnitOfWork) -> tuple[int, int]:
    application = uow.applications.add(Application(name="Shop"))
    assert application.id is not None
    sbom = uow.sboms.add(Sbom(application_id=application.id, name="backend-image"))
    assert sbom.id is not None
    return application.id, sbom.id


def _sbom_version(sbom_id: int, label: str) -> SbomVersion:
    return SbomVersion(
        sbom_id=sbom_id,
        label=label,
        uploaded_at=datetime(2026, 11, 21, 12, 0, tzinfo=UTC),
        serial_number="urn:uuid:1",
        is_current=True,
        entries=(
            SbomEntry(
                "react", "18.2.0", Category.LIBRARY, Ecosystem.NPM, True, "pkg:npm/react@18.2.0"
            ),
            SbomEntry("openssl", "3.0.11", Category.LIBRARY, None, False, None),
        ),
    )


def test_sbom_version_roundtrip_keeps_entries(uow: SqlAlchemyUnitOfWork) -> None:
    _, sbom_id = _app_with_sbom(uow)
    saved = uow.sbom_versions.add(_sbom_version(sbom_id, "v1"))
    uow.commit()
    assert saved.id is not None
    loaded = uow.sbom_versions.get(saved.id)
    assert loaded.entries == _sbom_version(sbom_id, "v1").entries
    assert loaded.label == "v1"
    assert loaded.serial_number == "urn:uuid:1"


def test_sbom_find_by_name_and_list(uow: SqlAlchemyUnitOfWork) -> None:
    application_id, sbom_id = _app_with_sbom(uow)
    found = uow.sboms.find_by_name(application_id, "backend-image")
    assert found is not None
    assert found.id == sbom_id
    assert uow.sboms.find_by_name(application_id, "frontend") is None
    assert [sbom.name for sbom in uow.sboms.list_for_application(application_id)] == [
        "backend-image"
    ]


def test_current_for_sbom_and_archive(uow: SqlAlchemyUnitOfWork) -> None:
    _, sbom_id = _app_with_sbom(uow)
    first = uow.sbom_versions.add(_sbom_version(sbom_id, "v1"))
    assert first.id is not None
    uow.sbom_versions.archive(first.id)
    second = uow.sbom_versions.add(_sbom_version(sbom_id, "v2"))
    uow.commit()
    current = uow.sbom_versions.current_for_sbom(sbom_id)
    assert current is not None
    assert current.id == second.id
    assert [v.label for v in uow.sbom_versions.list_for_sbom(sbom_id)] == ["v2", "v1"]


def test_component_roundtrip_keeps_sbom_id_and_checked(uow: SqlAlchemyUnitOfWork) -> None:
    application_id, sbom_id = _app_with_sbom(uow)
    component = uow.components.add(
        application_id,
        Component(
            "openssl", "3.0.11", Category.LIBRARY, None, True, sbom_id=sbom_id, checked=False
        ),
    )
    assert component.id is not None
    updated = uow.components.update(
        Component(
            "openssl",
            "3.0.11",
            Category.LIBRARY,
            None,
            False,
            id=component.id,
            application_id=application_id,
            sbom_id=sbom_id,
            checked=True,
        )
    )
    uow.commit()
    assert component.sbom_id == sbom_id
    assert component.checked is False
    assert updated.checked is True
    assert [c.id for c in uow.components.list_for_sbom(sbom_id)] == [component.id]


def test_delete_component_and_findings_for_component(uow: SqlAlchemyUnitOfWork) -> None:
    application_id, _ = _app_with_sbom(uow)
    component = uow.components.add(
        application_id, Component("react", "18.2.0", Category.LIBRARY, Ecosystem.NPM, True)
    )
    assert component.id is not None
    uow.advisories.upsert(_advisory())
    uow.findings.upsert(_finding(component.id, application_id))
    uow.findings.delete_for_components([component.id])
    uow.components.delete_many([component.id])
    uow.commit()
    assert uow.findings.list() == []
    assert uow.components.list_all() == []


def test_delete_sbom_removes_versions(uow: SqlAlchemyUnitOfWork) -> None:
    _, sbom_id = _app_with_sbom(uow)
    uow.sbom_versions.add(_sbom_version(sbom_id, "v1"))
    uow.sboms.delete(sbom_id)
    uow.commit()
    assert uow.sbom_versions.list_for_sbom(sbom_id) == []
    with pytest.raises(EntityNotFoundError):
        uow.sboms.get(sbom_id)


def test_bulk_add_and_delete_components_with_findings(uow: SqlAlchemyUnitOfWork) -> None:
    application_id, sbom_id = _app_with_sbom(uow)
    react = Component("react", "18.2.0", Category.LIBRARY, Ecosystem.NPM, True, sbom_id=sbom_id)
    openssl = Component(
        "openssl", "3.0.11", Category.LIBRARY, None, False, sbom_id=sbom_id, checked=False
    )
    uow.components.add_many(application_id, [react, openssl])
    stored = {c.name: c for c in uow.components.list_for_sbom(sbom_id)}
    assert stored["openssl"].checked is False
    react_id = stored["react"].id
    assert react_id is not None
    uow.advisories.upsert(_advisory())
    uow.findings.upsert(_finding(react_id, application_id))
    uow.findings.delete_for_components([react_id])
    uow.components.delete_many([react_id])
    uow.commit()
    assert uow.findings.list() == []
    assert [c.name for c in uow.components.list_for_sbom(sbom_id)] == ["openssl"]


def test_sbom_version_uploaded_at_is_utc_aware(uow: SqlAlchemyUnitOfWork) -> None:
    _, sbom_id = _app_with_sbom(uow)
    saved = uow.sbom_versions.add(_sbom_version(sbom_id, "v1"))
    uow.commit()
    uow._session.expire_all()
    assert saved.id is not None
    loaded = uow.sbom_versions.get(saved.id)
    assert loaded.uploaded_at.tzinfo is not None
    assert loaded.uploaded_at == datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


def test_application_github_settings_roundtrip(uow: SqlAlchemyUnitOfWork) -> None:
    application = uow.applications.add(Application(name="Shop"))
    application.github_repository = "acme/shop"
    application.auto_issue_min_level = Severity.HOCH
    application.auto_issue_enabled_at = datetime(2026, 11, 21, 10, 0, tzinfo=UTC)
    application.github_sync_message = "3 angelegt"
    uow.applications.update(application)

    assert application.id is not None
    loaded = uow.applications.get(application.id)
    assert loaded.github_repository == "acme/shop"
    assert loaded.auto_issue_min_level == Severity.HOCH
    assert loaded.auto_issue_enabled_at == datetime(2026, 11, 21, 10, 0, tzinfo=UTC)
    assert loaded.github_sync_message == "3 angelegt"
    assert loaded.github_synced_at is None


def _seeded_finding(uow: SqlAlchemyUnitOfWork) -> Finding:
    application = uow.applications.add(Application(name="Shop"))
    assert application.id is not None
    component = uow.components.add(
        application.id,
        Component(
            name="react",
            version="18.2.0",
            category=Category.LIBRARY,
            ecosystem=Ecosystem.NPM,
            direct=True,
        ),
    )
    assert component.id is not None
    uow.advisories.upsert(_advisory())
    return uow.findings.upsert(_finding(component.id, application.id))


def test_first_seen_is_stored_on_creation_and_never_overwritten(uow: SqlAlchemyUnitOfWork) -> None:
    seeded = _seeded_finding(uow)
    assert uow.findings.list()[0].first_seen_at is None  # ohne Zeitpunkt bleibt er leer
    component = uow.components.add(
        seeded.application_id,
        Component(
            name="vue",
            version="3.0.0",
            category=Category.LIBRARY,
            ecosystem=Ecosystem.NPM,
            direct=True,
        ),
    )
    assert component.id is not None
    first = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)
    later = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)

    created = _finding(component.id, seeded.application_id)
    created.first_seen_at = first
    uow.findings.upsert(created)
    again = _finding(component.id, seeded.application_id)
    again.first_seen_at = later
    uow.findings.upsert(again)

    stored = next(item for item in uow.findings.list() if item.component_id == component.id)
    assert stored.first_seen_at == first


def test_finding_issue_link_roundtrip(uow: SqlAlchemyUnitOfWork) -> None:
    finding = _seeded_finding(uow)
    assert finding.id is not None

    uow.findings.save_issue_link(
        finding.id, "https://github.com/acme/shop/issues/7", IssueState.CLOSED
    )

    loaded = uow.findings.list()[0]
    assert loaded.issue_url == "https://github.com/acme/shop/issues/7"
    assert loaded.issue_state == IssueState.CLOSED
