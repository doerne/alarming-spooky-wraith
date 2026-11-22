from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.domain.inventory import Application
from app.presentation.app_factory import AppServices, create_app
from tests.fakes import InMemoryUnitOfWork, TupleVersionComparator

_NOW = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)


def _client() -> TestClient:
    uow = InMemoryUnitOfWork()
    uow.applications.add(Application(name="Shop"))

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
