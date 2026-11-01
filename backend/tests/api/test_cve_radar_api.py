from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from functools import partial

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.application.component_matching import ComponentMatcher
from app.application.ingest import run_ingest_job
from app.application.ingest_runner import IngestRunState
from app.application.source_registry import SourceRegistry
from app.domain.ports import SourceVuln
from app.infrastructure.thread_ingest_runner import ThreadIngestRunner
from app.infrastructure.univers_matcher import UniversVersionMatcher
from app.presentation.app_factory import AppServices, create_app
from tests.fakes import (
    FakeAdvisoryStore,
    FakeIngestRunner,
    FakePackageSource,
    InMemoryUnitOfWork,
    descriptor,
)

_WAIT_SECONDS = 5


def _build(vulns: list[SourceVuln]) -> FastAPI:
    uow = InMemoryUnitOfWork()

    @contextmanager
    def factory() -> Iterator[InMemoryUnitOfWork]:
        yield uow

    registry = SourceRegistry([FakePackageSource(descriptor("osv"), {"react": vulns})])
    matcher = ComponentMatcher(UniversVersionMatcher())
    store = FakeAdvisoryStore()

    runner = ThreadIngestRunner(
        partial(run_ingest_job, factory, registry, matcher, store, _now), _now
    )
    return create_app(
        factory,
        services=AppServices(ingest_runner=runner, source_registry=registry, advisory_store=store),
    )


def _now() -> datetime:
    return datetime.now(UTC)


def _ingest(client: TestClient) -> dict[str, object]:
    """Startet den Lauf, wartet auf den Hintergrund-Thread und liefert den Status."""
    response = client.post("/api/ingest/run")
    assert response.status_code == 202
    runner: ThreadIngestRunner = client.app.state.ingest_runner  # type: ignore[attr-defined]
    assert runner.wait(_WAIT_SECONDS)
    status: dict[str, object] = client.get("/api/ingest/status").json()
    return status


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


_VULN = SourceVuln(
    source_key="osv",
    url="https://osv.dev/vulnerability",
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

    status = _ingest(client)
    assert status["running"] is False
    assert status["componentsScanned"] == 1
    assert status["findingsFound"] == 1
    assert status["error"] is None

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

    assert _ingest(client)["findingsFound"] == 0
    page = client.get("/api/cves").json()
    assert page == {"items": [], "total": 0, "unfilteredTotal": 0}


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
    _ingest(client)

    shop_id = client.get("/api/applications").json()[0]["id"]
    page = client.get(f"/api/cves?application_id={shop_id}").json()
    assert page["total"] == 1
    assert page["items"][0]["applicationName"] == "Shop"


def test_component_with_pypi_ecosystem_is_accepted() -> None:
    client = _client(_build([]))
    app_id = client.post("/api/applications", json={"name": "Api"}).json()["id"]
    response = client.post(
        f"/api/applications/{app_id}/components",
        json={
            "name": "django",
            "version": "5.1.0",
            "category": "framework",
            "ecosystem": "PyPI",
            "direct": True,
        },
    )
    assert response.status_code == 201
    assert response.json()["ecosystem"] == "PyPI"


def _app_with_runner(runner: FakeIngestRunner) -> FastAPI:
    uow = InMemoryUnitOfWork()

    @contextmanager
    def factory() -> Iterator[InMemoryUnitOfWork]:
        yield uow

    return create_app(
        factory, services=AppServices(ingest_runner=runner, source_registry=SourceRegistry([]))
    )


def test_second_start_is_rejected() -> None:
    client = _client(_app_with_runner(FakeIngestRunner(IngestRunState(running=True))))
    response = client.post("/api/ingest/run")
    assert response.status_code == 409
    assert response.json()["detail"] == "Ein Scan läuft bereits"


def test_start_returns_running_state() -> None:
    runner = FakeIngestRunner()
    response = _client(_app_with_runner(runner)).post("/api/ingest/run")
    assert response.status_code == 202
    assert response.json()["running"] is True
    assert runner.starts == 1


def test_status_endpoint() -> None:
    finished = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    state = IngestRunState(
        running=False,
        started_at=finished,
        finished_at=finished,
        components_scanned=4,
        findings_found=2,
    )
    body = _client(_app_with_runner(FakeIngestRunner(state))).get("/api/ingest/status").json()
    assert body["running"] is False
    assert body["componentsScanned"] == 4
    assert body["findingsFound"] == 2
    assert body["finishedAt"].startswith("2026-11-01T12:00:00")


def test_cve_detail_returns_document_and_findings() -> None:
    client = _client(_build([_VULN]))
    _add_react(client)
    _ingest(client)
    response = client.get("/api/cves/CVE-2024-123")
    assert response.status_code == 200
    body = response.json()
    assert body["advisoryId"] == "CVE-2024-123"
    assert body["cvssBase"] == 9.8
    assert body["fixVersion"] == "18.2.1"
    assert body["riskLevel"] == "kritisch"
    assert body["sources"][0]["sourceKey"] == "osv"
    assert body["findings"][0]["applicationName"] == "Shop"
    assert body["findings"][0]["componentName"] == "react"
    assert isinstance(body["findings"][0]["componentId"], int)
    assert isinstance(body["references"], list)


def test_unknown_advisory_is_404() -> None:
    client = _client(_build([]))
    assert client.get("/api/cves/CVE-1999-0001").status_code == 404


def test_list_items_carry_component_id() -> None:
    client = _client(_build([_VULN]))
    _add_react(client)
    _ingest(client)
    item = client.get("/api/cves").json()["items"][0]
    assert isinstance(item["componentId"], int)


_MEDIUM = SourceVuln(
    source_key="osv",
    url="https://osv.dev/vulnerability",
    id="GHSA-m",
    aliases=["CVE-2024-500"],
    summary="Medium issue",
    details="d",
    cvss_base=5.0,
    fixed_version=None,
    references=[],
)


def _filtered_client() -> TestClient:
    client = _client(_build([_VULN, _MEDIUM]))
    _add_react(client)
    _ingest(client)
    return client


def test_filter_query_params() -> None:
    body = _filtered_client().get("/api/cves?severity=kritisch").json()
    assert [item["advisoryId"] for item in body["items"]] == ["CVE-2024-123"]
    assert body["total"] == 1
    assert body["unfilteredTotal"] == 2
    assert isinstance(body["items"][0]["applicationId"], int)


def test_multiple_values_are_or() -> None:
    body = _filtered_client().get("/api/cves?severity=kritisch&severity=mittel").json()
    assert body["total"] == 2


def test_unknown_severity_is_422() -> None:
    assert _filtered_client().get("/api/cves?severity=egal").status_code == 422


def test_ecosystem_none_and_query() -> None:
    client = _filtered_client()
    assert client.get("/api/cves?ecosystem=none").json()["total"] == 0
    assert client.get("/api/cves?ecosystem=npm&q=medium").json()["total"] == 1
