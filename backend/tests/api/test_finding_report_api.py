from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.domain.inventory import Category, Component, Ecosystem
from app.domain.vulnerability import Advisory, Finding, RiskScore, Severity
from app.presentation.app_factory import AppServices, create_app
from tests.fakes import InMemoryUnitOfWork

_NOW = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)


def _client() -> tuple[TestClient, int]:
    uow = InMemoryUnitOfWork()

    @contextmanager
    def factory() -> Iterator[InMemoryUnitOfWork]:
        yield uow

    client = TestClient(create_app(factory, services=AppServices(clock=lambda: _NOW)))
    application_id: int = client.post("/api/applications", json={"name": "Shop"}).json()["id"]
    component = uow.components.add(
        application_id, Component("react", "18.2.0", Category.LIBRARY, Ecosystem.NPM, True)
    )
    assert component.id is not None
    uow.advisories.upsert(Advisory("CVE-1", "CVE-1", "t", "d", 9.8, None, [], ""))
    uow.findings.upsert(
        Finding(
            "CVE-1",
            component.id,
            application_id,
            "18.2.0",
            RiskScore(value=98, level=Severity.KRITISCH, rationale=""),
        )
    )
    return client, application_id


def test_patch_reports_issue_and_status() -> None:
    client, application_id = _client()
    response = client.patch(
        f"/api/applications/{application_id}/cves/CVE-1",
        json={"issueUrl": "https://github.com/acme/shop/issues/12", "status": "behoben"},
    )
    assert response.status_code == 200
    assert response.json() == {"advisoryId": "CVE-1", "updated": 1}
    finding = client.get(f"/api/cves?application_id={application_id}").json()["items"][0]
    assert finding["status"] == "behoben"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"issueUrl": "javascript:alert(1)"},
        {"issueUrl": "https://github.com/x\n## Neu"},
        {"issueUrl": "https://github.com/x\u001b[31m"},
        {"issueUrl": "https://github.com/x\u007f"},
        {"issueUrl": "https://x/a)[b](javascript:x)"},
        {"issueUrl": "https://x/`code`"},
        {"issueUrl": "https://example.org/" + "x" * 500},
        {"comment": "x" * 2001},
        {"status": "erledigt"},
    ],
)
def test_patch_rejects_invalid_bodies(body: dict[str, object]) -> None:
    client, application_id = _client()
    response = client.patch(f"/api/applications/{application_id}/cves/CVE-1", json=body)
    assert response.status_code == 422


def test_patch_unknown_cve_returns_404() -> None:
    client, application_id = _client()
    response = client.patch(
        f"/api/applications/{application_id}/cves/CVE-404", json={"status": "behoben"}
    )
    assert response.status_code == 404
