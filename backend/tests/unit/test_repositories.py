import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.domain.errors import EntityNotFoundError
from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.vulnerability import Advisory, Finding, RiskScore, Severity
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
