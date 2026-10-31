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


def test_list_applications_returns_created_ones() -> None:
    client = _client(_build([]))
    client.post("/api/applications", json={"name": "Shop"})
    client.post("/api/applications", json={"name": "Blog"})

    names = [app["name"] for app in client.get("/api/applications").json()]
    assert names == ["Shop", "Blog"]


def test_get_application_returns_components() -> None:
    client = _client(_build([]))
    _add_react(client)
    app_id = client.get("/api/applications").json()[0]["id"]

    detail = client.get(f"/api/applications/{app_id}").json()
    assert detail["name"] == "Shop"
    assert [c["name"] for c in detail["components"]] == ["react"]
    assert detail["components"][0]["version"] == "18.2.0"


def test_get_unknown_application_is_404() -> None:
    client = _client(_build([]))
    assert client.get("/api/applications/999").status_code == 404


def test_update_component_changes_fields() -> None:
    client = _client(_build([]))
    _add_react(client)
    app_id = client.get("/api/applications").json()[0]["id"]
    comp_id = client.get(f"/api/applications/{app_id}").json()["components"][0]["id"]

    response = client.put(
        f"/api/applications/{app_id}/components/{comp_id}",
        json={
            "name": "react",
            "version": "18.3.0",
            "category": "framework",
            "ecosystem": "npm",
            "direct": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["version"] == "18.3.0"
    assert body["category"] == "framework"
    assert body["direct"] is False

    detail = client.get(f"/api/applications/{app_id}").json()
    assert [c["version"] for c in detail["components"]] == ["18.3.0"]


def test_update_unknown_component_is_404() -> None:
    client = _client(_build([]))
    app_id = client.post("/api/applications", json={"name": "Shop"}).json()["id"]

    response = client.put(
        f"/api/applications/{app_id}/components/999",
        json={
            "name": "x",
            "version": "1",
            "category": "library",
            "ecosystem": None,
            "direct": True,
        },
    )
    assert response.status_code == 404


def test_update_component_of_other_application_is_404() -> None:
    client = _client(_build([]))
    _add_react(client)
    shop_id = client.get("/api/applications").json()[0]["id"]
    comp_id = client.get(f"/api/applications/{shop_id}").json()["components"][0]["id"]
    other_id = client.post("/api/applications", json={"name": "Blog"}).json()["id"]

    response = client.put(
        f"/api/applications/{other_id}/components/{comp_id}",
        json={
            "name": "react",
            "version": "19",
            "category": "library",
            "ecosystem": "npm",
            "direct": True,
        },
    )
    assert response.status_code == 404


def test_list_cves_filtered_by_application() -> None:
    client = _client(_build([_VULN]))
    _add_react(client)  # Shop
    other = client.post("/api/applications", json={"name": "Blog"}).json()["id"]
    client.post(
        f"/api/applications/{other}/components",
        json={
            "name": "react",
            "version": "18.2.0",
            "category": "library",
            "ecosystem": "npm",
            "direct": True,
        },
    )
    client.post("/api/ingest/run")

    shop_id = client.get("/api/applications").json()[0]["id"]
    page = client.get(f"/api/cves?application_id={shop_id}").json()
    assert page["total"] == 1
    assert page["items"][0]["applicationName"] == "Shop"
