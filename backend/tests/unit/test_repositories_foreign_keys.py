"""Repository-Tests mit eingeschalteten Fremdschlüsseln (wie MariaDB)."""

from typing import Any

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.application.alias_absorber import AliasAbsorber
from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.vulnerability import Advisory, Finding, FindingStatus, RiskScore, Severity
from app.infrastructure import models  # noqa: F401  (Modelle registrieren)
from app.infrastructure.database import Base
from app.infrastructure.models import AdvisoryAliasModel
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from tests.fakes import FakeAdvisoryStore


def _enable_foreign_keys(connection: Any, _: Any) -> None:
    connection.execute("PRAGMA foreign_keys=ON")


@pytest.fixture
def uow() -> SqlAlchemyUnitOfWork:
    engine = create_engine("sqlite://")
    event.listen(engine, "connect", _enable_foreign_keys)
    Base.metadata.create_all(engine)
    return SqlAlchemyUnitOfWork(Session(engine))


def _alias_target(uow: SqlAlchemyUnitOfWork, alias_id: str) -> str | None:
    model = uow._session.get(AdvisoryAliasModel, alias_id)
    return model.advisory_id if model else None


def _advisory(advisory_id: str) -> Advisory:
    return Advisory(advisory_id, None, "t", "d", 7.5, None, [], f"advisories/{advisory_id}.md")


def _setup(uow: SqlAlchemyUnitOfWork) -> tuple[int, int]:
    application = uow.applications.add(Application(name="Shop"))
    assert application.id is not None
    component = uow.components.add(
        application.id, Component("certifi", "1.0", Category.LIBRARY, Ecosystem.PYPI, True)
    )
    assert component.id is not None
    for advisory_id in ("GHSA-1", "PYSEC-1"):
        uow.advisories.upsert(_advisory(advisory_id))
    return application.id, component.id


def _finding(advisory_id: str, component_id: int, application_id: int) -> Finding:
    return Finding(
        advisory_id=advisory_id,
        component_id=component_id,
        application_id=application_id,
        found_version="1.0",
        risk=RiskScore(value=75, level=Severity.HOCH, rationale=""),
    )


def test_finding_reassign_save_triage_delete(uow: SqlAlchemyUnitOfWork) -> None:
    application_id, component_id = _setup(uow)
    stored = uow.findings.upsert(_finding("PYSEC-1", component_id, application_id))
    assert stored.id is not None
    uow.findings.reassign(stored.id, "GHSA-1")
    uow.findings.save_triage(stored.id, FindingStatus.ACCEPTED, "ok")
    uow.commit()
    [moved] = uow.findings.list_for_advisory("GHSA-1")
    assert (moved.status, moved.comment) == (FindingStatus.ACCEPTED, "ok")
    assert uow.findings.list_for_advisory("PYSEC-1") == []
    uow.findings.delete(stored.id)
    uow.commit()
    assert uow.findings.list() == []


def test_advisory_find_delete(uow: SqlAlchemyUnitOfWork) -> None:
    _setup(uow)
    assert uow.advisories.find("PYSEC-1") is not None
    assert uow.advisories.find("UNKNOWN") is None
    uow.advisories.delete("PYSEC-1")
    uow.commit()
    assert uow.advisories.find("PYSEC-1") is None


def test_advisory_alias_remove_and_repoint(uow: SqlAlchemyUnitOfWork) -> None:
    uow.advisory_aliases.save("PYSEC-1", "GHSA-1")
    uow.advisory_aliases.save("OSV-1", "GHSA-1")
    uow.advisory_aliases.save("GHSA-1", "OLD")
    uow.advisory_aliases.repoint("GHSA-1", "CVE-2026-1")
    uow.advisory_aliases.remove("GHSA-1")
    uow.commit()
    assert _alias_target(uow, "PYSEC-1") == "CVE-2026-1"
    assert _alias_target(uow, "OSV-1") == "CVE-2026-1"
    assert _alias_target(uow, "GHSA-1") is None


def test_advisory_alias_save_resolve_overwrites(uow: SqlAlchemyUnitOfWork) -> None:
    uow.advisory_aliases.save("PYSEC-1", "GHSA-1")
    uow.advisory_aliases.save("PYSEC-1", "CVE-2026-1")
    uow.advisory_aliases.save("PYSEC-1", "CVE-2026-1")
    uow.commit()
    assert _alias_target(uow, "PYSEC-1") == "CVE-2026-1"
    assert _alias_target(uow, "UNKNOWN") is None


def test_absorber_runs_with_foreign_keys(uow: SqlAlchemyUnitOfWork) -> None:
    application_id, component_id = _setup(uow)
    other = uow.components.add(
        application_id, Component("pip", "1.0", Category.LIBRARY, Ecosystem.PYPI, True)
    )
    assert other.id is not None
    uow.findings.upsert(_finding("GHSA-1", component_id, application_id))
    uow.findings.upsert(_finding("PYSEC-1", component_id, application_id))
    uow.findings.upsert(_finding("PYSEC-1", other.id, application_id))
    AliasAbsorber(uow, FakeAdvisoryStore()).absorb("GHSA-1", ["PYSEC-1"])
    uow.commit()
    assert sorted(
        finding.component_id for finding in uow.findings.list_for_advisory("GHSA-1")
    ) == sorted([component_id, other.id])
    assert uow.advisories.find("PYSEC-1") is None
    assert _alias_target(uow, "PYSEC-1") == "GHSA-1"
