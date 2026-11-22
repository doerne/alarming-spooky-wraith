from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.presentation.app_factory import AppServices, create_app
from tests.fakes import FakeJobActivity, InMemoryUnitOfWork, fixed_clock


def _client(activity: FakeJobActivity | None = None) -> TestClient:
    uow = InMemoryUnitOfWork()

    @contextmanager
    def factory() -> Iterator[InMemoryUnitOfWork]:
        yield uow

    return TestClient(
        create_app(factory, services=AppServices(job_activity=activity, clock=fixed_clock))
    )


def _create(client: TestClient) -> int:
    application_id: int = client.post("/api/applications", json={"name": "Shop"}).json()["id"]
    return application_id


def test_delete_returns_204_then_application_is_gone() -> None:
    client = _client()
    application_id = _create(client)
    assert client.delete(f"/api/applications/{application_id}").status_code == 204
    assert client.get(f"/api/applications/{application_id}").status_code == 404


def test_delete_unknown_application_is_404() -> None:
    assert _client().delete("/api/applications/999").status_code == 404


def test_delete_while_busy_is_409() -> None:
    client = _client(FakeJobActivity(busy=True))
    application_id = _create(client)
    response = client.delete(f"/api/applications/{application_id}")
    assert response.status_code == 409
    assert client.get(f"/api/applications/{application_id}").status_code == 200
