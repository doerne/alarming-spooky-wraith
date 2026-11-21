from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.domain.vulnerability import Severity
from app.presentation.app_factory import AppServices, create_app
from tests.fakes import FakeIssueTracker, FakeSyncRunner, InMemoryUnitOfWork

_NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


def _client(
    uow: InMemoryUnitOfWork,
    tracker: FakeIssueTracker | None = None,
    runner: FakeSyncRunner | None = None,
) -> TestClient:
    @contextmanager
    def factory() -> Iterator[InMemoryUnitOfWork]:
        yield uow

    services = AppServices(
        clock=lambda: _NOW,
        github_tracker=tracker or FakeIssueTracker(),
        github_sync_runner=runner or FakeSyncRunner(),
    )
    return TestClient(create_app(factory, services=services))


def _application(client: TestClient) -> int:
    response = client.post("/api/applications", json={"name": "Shop"})
    return int(response.json()["id"])


def test_patch_sets_repository_and_threshold_and_detail_shows_them() -> None:
    uow = InMemoryUnitOfWork()
    client = _client(uow)
    application_id = _application(client)

    response = client.patch(
        f"/api/applications/{application_id}",
        json={"githubRepository": "acme/shop", "autoIssueMinLevel": "hoch"},
    )

    assert response.status_code == 200
    detail = client.get(f"/api/applications/{application_id}").json()
    assert detail["githubRepository"] == "acme/shop"
    assert detail["autoIssueMinLevel"] == "hoch"
    assert detail["githubSyncedAt"] is None
    assert detail["githubSyncMessage"] == ""
    assert uow.applications.get(application_id).auto_issue_min_level == Severity.HOCH


def test_patch_with_null_removes_repository() -> None:
    client = _client(InMemoryUnitOfWork())
    application_id = _application(client)
    client.patch(f"/api/applications/{application_id}", json={"githubRepository": "acme/shop"})

    client.patch(f"/api/applications/{application_id}", json={"githubRepository": None})

    assert client.get(f"/api/applications/{application_id}").json()["githubRepository"] is None


def test_patch_rejects_malformed_repository_and_stores_nothing() -> None:
    uow = InMemoryUnitOfWork()
    client = _client(uow)
    application_id = _application(client)

    for value in ("acme/shop\nx", "../shop", "acme/..", "acme"):
        response = client.patch(
            f"/api/applications/{application_id}", json={"githubRepository": value}
        )
        assert response.status_code == 422
    assert uow.applications.get(application_id).github_repository is None


def test_status_reports_configuration_and_running_state() -> None:
    client = _client(InMemoryUnitOfWork(), FakeIssueTracker(configured=False))

    assert client.get("/api/github/status").json() == {"configured": False, "running": False}


def test_sync_start_is_accepted_and_passes_the_request_on() -> None:
    uow = InMemoryUnitOfWork()
    runner = FakeSyncRunner()
    client = _client(uow, runner=runner)
    application_id = _application(client)
    client.patch(f"/api/applications/{application_id}", json={"githubRepository": "acme/shop"})

    response = client.post(
        f"/api/applications/{application_id}/github/sync",
        json={"createIssues": True, "minLevel": "hoch"},
    )

    assert response.status_code == 202
    [request] = runner.requests
    assert request.application_id == application_id
    assert request.create_issues is True
    assert request.min_level == Severity.HOCH


def test_sync_is_refused_while_a_job_runs() -> None:
    client = _client(InMemoryUnitOfWork(), runner=FakeSyncRunner(busy=True))
    application_id = _application(client)
    client.patch(f"/api/applications/{application_id}", json={"githubRepository": "acme/shop"})

    response = client.post(
        f"/api/applications/{application_id}/github/sync", json={"createIssues": False}
    )

    assert response.status_code == 409


def test_sync_without_configuration_is_unavailable() -> None:
    client = _client(InMemoryUnitOfWork(), FakeIssueTracker(configured=False))
    application_id = _application(client)
    client.patch(f"/api/applications/{application_id}", json={"githubRepository": "acme/shop"})

    response = client.post(
        f"/api/applications/{application_id}/github/sync", json={"createIssues": False}
    )

    assert response.status_code == 503


def test_sync_without_repository_is_a_conflict() -> None:
    client = _client(InMemoryUnitOfWork())
    application_id = _application(client)

    response = client.post(
        f"/api/applications/{application_id}/github/sync", json={"createIssues": False}
    )

    assert response.status_code == 409


def test_sync_for_unknown_application_is_not_found() -> None:
    client = _client(InMemoryUnitOfWork())

    response = client.post("/api/applications/999/github/sync", json={"createIssues": False})

    assert response.status_code == 404
