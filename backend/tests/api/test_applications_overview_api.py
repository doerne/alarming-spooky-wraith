from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.presentation.app_factory import AppServices, create_app
from tests.fakes import InMemoryUnitOfWork, fixed_clock

_KEYS = {
    "id",
    "name",
    "description",
    "openBySeverity",
    "overdue",
    "componentCount",
    "latestSbomUploadAt",
    "sbomStale",
    "scanState",
    "inventoryChangedAt",
    "githubRepository",
}


def _client() -> TestClient:
    uow = InMemoryUnitOfWork()

    @contextmanager
    def factory() -> Iterator[InMemoryUnitOfWork]:
        yield uow

    return TestClient(create_app(factory, services=AppServices(clock=fixed_clock)))


def test_overview_lists_applications_in_camel_case() -> None:
    client = _client()
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

    response = client.get("/api/applications/overview")

    assert response.status_code == 200
    [row] = response.json()
    assert set(row) == _KEYS
    assert row["openBySeverity"] == {"kritisch": 0, "hoch": 0, "mittel": 0, "niedrig": 0}
    assert row["componentCount"] == 1
    assert row["scanState"] == "never_scanned"
    assert row["sbomStale"] is True


def test_overview_is_not_read_as_application_id() -> None:
    response = _client().get("/api/applications/overview")
    assert response.status_code == 200
    assert response.json() == []
