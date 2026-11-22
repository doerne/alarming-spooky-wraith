from datetime import UTC, datetime

import pytest

from app.application.remediation_kpis import GetRemediationKpis
from app.domain.errors import EntityNotFoundError
from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.vulnerability import Advisory, Finding, FindingStatus, RiskScore, Severity
from tests.fakes import InMemoryUnitOfWork, TupleVersionComparator

_NOW = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)


def _add_finding(
    uow: InMemoryUnitOfWork,
    application_name: str,
    status: FindingStatus = FindingStatus.OPEN,
    advisory_id: str = "CVE-1",
) -> int:
    application = uow.applications.add(Application(name=application_name))
    assert application.id is not None
    component = uow.components.add(
        application.id, Component("react", "1.0", Category.LIBRARY, Ecosystem.NPM, True)
    )
    assert component.id is not None
    uow.advisories.upsert(
        Advisory(advisory_id, advisory_id, "Titel", "", None, "1.2", [], "okf/x.md")
    )
    uow.findings.upsert(
        Finding(
            advisory_id,
            component.id,
            application.id,
            "1.0",
            RiskScore(value=75, level=Severity.HOCH, rationale=""),
            status=status,
        )
    )
    return application.id


def _use_case(uow: InMemoryUnitOfWork) -> GetRemediationKpis:
    return GetRemediationKpis(uow, lambda: _NOW, TupleVersionComparator())


def test_same_package_in_two_applications_is_one_target() -> None:
    uow = InMemoryUnitOfWork()
    _add_finding(uow, "Shop")
    _add_finding(uow, "Blog")
    kpis = _use_case(uow).execute()
    assert len(kpis.updates.targets) == 1
    assert kpis.updates.targets[0].applications == 2
    assert kpis.updates.targets[0].target_version == "1.2"


def test_scoped_to_application() -> None:
    uow = InMemoryUnitOfWork()
    shop_id = _add_finding(uow, "Shop")
    _add_finding(uow, "Blog")
    kpis = _use_case(uow).execute(application_id=shop_id)
    assert kpis.updates.open_total == 1
    assert kpis.updates.targets[0].applications == 1


def test_closed_findings_are_not_counted() -> None:
    uow = InMemoryUnitOfWork()
    _add_finding(uow, "Shop")
    _add_finding(uow, "Blog", status=FindingStatus.FIXED)
    assert _use_case(uow).execute().updates.open_total == 1


def test_unknown_application_raises() -> None:
    with pytest.raises(EntityNotFoundError):
        _use_case(InMemoryUnitOfWork()).execute(application_id=999)
