from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.domain.inventory import Category, Component, Ecosystem
from app.domain.vulnerability import Advisory, Finding, RiskScore, Severity
from app.presentation.app_factory import AppServices, create_app
from tests.fakes import FakeAdvisoryStore, InMemoryUnitOfWork

_NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


def _client(uow: InMemoryUnitOfWork) -> TestClient:
    @contextmanager
    def factory() -> Iterator[InMemoryUnitOfWork]:
        yield uow

    services = AppServices(advisory_store=FakeAdvisoryStore(), clock=lambda: _NOW)
    return TestClient(create_app(factory, services=services))


def test_export_returns_markdown_attachment() -> None:
    uow = InMemoryUnitOfWork()
    client = _client(uow)
    application_id = client.post("/api/applications", json={"name": "Mein Shop"}).json()["id"]
    component = uow.components.add(
        application_id, Component("react", "18.2.0", Category.LIBRARY, Ecosystem.NPM, True)
    )
    assert component.id is not None
    uow.advisories.upsert(Advisory("CVE-2024-1", "CVE-2024-1", "XSS", "d", 9.8, "18.2.1", [], ""))
    uow.findings.upsert(
        Finding(
            "CVE-2024-1",
            component.id,
            application_id,
            "18.2.0",
            RiskScore(value=98, level=Severity.KRITISCH, rationale=""),
        )
    )

    response = client.get(f"/api/applications/{application_id}/cves/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert (
        'filename="cve-issues-mein-shop-2026-11-21.md"' in response.headers["content-disposition"]
    )
    assert f"<!-- cve-radar:application={application_id};advisory=CVE-2024-1 -->" in response.text


def test_export_unknown_application_returns_404() -> None:
    response = _client(InMemoryUnitOfWork()).get("/api/applications/999/cves/export")
    assert response.status_code == 404
