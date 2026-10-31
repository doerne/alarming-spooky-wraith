from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.ports import OsvVuln
from app.presentation.app_factory import create_app
from tests.fakes import FakeAdvisoryStore, FakeOsvClient, InMemoryUnitOfWork


def _build(vulns: list[OsvVuln]) -> FastAPI:
    uow = InMemoryUnitOfWork()

    @contextmanager
    def factory() -> Iterator[InMemoryUnitOfWork]:
        yield uow

    return create_app(
        factory,
        osv_client=FakeOsvClient({"react": vulns}),
        advisory_store=FakeAdvisoryStore(),
    )


def _client(app: FastAPI) -> TestClient:
    return TestClient(app)


def _add_react(client: TestClient) -> None:
    app_id = client.post("/api/applications", json={"name": "Shop"}).json()["id"]
    client.post(
        f"/api/applications/{app_id}/components",
        json={
            "name": "react",
            "version": "18.2.0",
            "category": "library",
            "ecosystem": "npm",
            "direct": True,
        },
    )


_VULN = OsvVuln(
    id="GHSA-x",
    aliases=["CVE-2024-123"],
    summary="XSS in react",
    details="d",
    cvss_base=9.8,
    fixed_version="18.2.1",
    references=["https://nvd.nist.gov/vuln/detail/CVE-2024-123"],
)


def test_ingest_then_list_returns_finding() -> None:
    client = _client(_build([_VULN]))
    _add_react(client)

    ingest = client.post("/api/ingest/run").json()
    assert ingest == {"componentsScanned": 1, "findingsFound": 1}

    page = client.get("/api/cves").json()
    assert page["total"] == 1
    item = page["items"][0]
    assert item["advisoryId"] == "CVE-2024-123"
    assert item["riskLevel"] == "kritisch"
    assert item["applicationName"] == "Shop"
    assert item["fixVersion"] == "18.2.1"


def test_ingest_without_vulns_is_empty() -> None:
    client = _client(_build([]))
    _add_react(client)

    assert client.post("/api/ingest/run").json()["findingsFound"] == 0
    page = client.get("/api/cves").json()
    assert page == {"items": [], "total": 0}


def test_create_application_returns_id() -> None:
    client = _client(_build([]))
    response = client.post("/api/applications", json={"name": "Shop"})
    assert response.status_code == 201
    assert response.json()["name"] == "Shop"
