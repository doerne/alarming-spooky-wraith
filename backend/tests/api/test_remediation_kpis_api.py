from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.vulnerability import Advisory, Finding, RiskScore, Severity
from app.presentation.app_factory import AppServices, create_app
from tests.fakes import InMemoryUnitOfWork, TupleVersionComparator

_NOW = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)


def _add_fixable_finding(uow: InMemoryUnitOfWork) -> None:
    component = uow.components.add(
        1, Component("react", "1.0", Category.LIBRARY, Ecosystem.NPM, True)
    )
    assert component.id is not None
    uow.advisories.upsert(Advisory("CVE-1", "CVE-1", "Titel", "", None, "1.2", [], "okf/x.md"))
    uow.findings.upsert(
        Finding(
            "CVE-1",
            component.id,
            1,
            "1.0",
            RiskScore(value=75, level=Severity.KRITISCH, rationale=""),
            first_seen_at=datetime(2026, 11, 22, tzinfo=UTC),
        )
    )


def _client(with_finding: bool = False) -> TestClient:
    uow = InMemoryUnitOfWork()
    uow.applications.add(Application(name="Shop"))
    if with_finding:
        _add_fixable_finding(uow)

    @contextmanager
    def factory() -> Iterator[InMemoryUnitOfWork]:
        yield uow

    services = AppServices(clock=lambda: _NOW, version_comparator=TupleVersionComparator())
    return TestClient(create_app(factory, services=services))


def test_get_kpis() -> None:
    response = _client().get("/api/findings/kpis")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"deadlines", "updates"}
    assert set(body["deadlines"]) == {"overdue", "dueSoon", "overdueBySeverity", "nextDueAt"}
    assert set(body["updates"]) == {"targets", "fixableOpen", "openTotal", "morePackages"}


def test_get_kpis_for_known_application() -> None:
    assert _client().get("/api/findings/kpis?applicationId=1").status_code == 200


def test_get_kpis_unknown_application_404() -> None:
    assert _client().get("/api/findings/kpis?applicationId=999").status_code == 404


def test_get_kpis_values_with_fixable_finding() -> None:
    body = _client(with_finding=True).get("/api/findings/kpis").json()
    target = body["updates"]["targets"][0]
    assert target == {
        "packageName": "react",
        "ecosystem": "npm",
        "targetVersion": "1.2",
        "findings": 1,
        "applications": 1,
    }
    assert (body["updates"]["fixableOpen"], body["updates"]["openTotal"]) == (1, 1)
    assert set(body["deadlines"]["overdueBySeverity"]) == {s.value for s in Severity}
    assert body["deadlines"]["nextDueAt"] == "2026-11-29T00:00:00Z"
