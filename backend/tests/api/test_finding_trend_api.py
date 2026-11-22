from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.domain.finding_trend import TREND_WEEK_OPTIONS
from app.presentation.app_factory import AppServices, create_app
from tests.fakes import InMemoryUnitOfWork

_NOW = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)


def _client() -> TestClient:
    uow = InMemoryUnitOfWork()

    @contextmanager
    def factory() -> Iterator[InMemoryUnitOfWork]:
        yield uow

    return TestClient(create_app(factory, services=AppServices(clock=lambda: _NOW)))


def test_get_trend_default_twelve_weeks() -> None:
    response = _client().get("/api/findings/trend")
    assert response.status_code == 200
    body = response.json()
    assert len(body["weeks"]) == 12
    assert set(body["weeks"][0]) == {"weekStart", "new", "closed", "openAtEnd"}
    assert body["weeks"][-1]["weekStart"] == "2026-11-16"
    assert set(body["openBySeverityNow"]) == {"kritisch", "hoch", "mittel", "niedrig"}


def test_get_trend_rejects_unsupported_weeks() -> None:
    assert _client().get("/api/findings/trend?weeks=5").status_code == 422


def test_get_trend_unknown_application_404() -> None:
    assert _client().get("/api/findings/trend?applicationId=999").status_code == 404


@pytest.mark.parametrize("weeks", TREND_WEEK_OPTIONS)
def test_get_trend_accepts_every_supported_range(weeks: int) -> None:
    # Das Frontend schickt weeks immer als Query-Text mit.
    response = _client().get(f"/api/findings/trend?weeks={weeks}")
    assert response.status_code == 200
    assert len(response.json()["weeks"]) == weeks


def test_get_trend_for_known_application() -> None:
    client = _client()
    application_id = client.post("/api/applications", json={"name": "Shop"}).json()["id"]
    response = client.get(f"/api/findings/trend?weeks=4&applicationId={application_id}")
    assert response.status_code == 200
    assert response.json()["untouchedNow"] == 0
