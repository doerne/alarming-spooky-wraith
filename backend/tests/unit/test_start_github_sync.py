import pytest

from app.application.github_start import StartGitHubSync
from app.application.github_sync import SyncRequest
from app.domain.errors import ConflictError, IssueTrackerError
from app.domain.inventory import Application
from app.domain.vulnerability import Severity
from tests.fakes import FakeIssueTracker, FakeSyncRunner, InMemoryUnitOfWork


def _uow(repository: str | None = "acme/shop") -> tuple[InMemoryUnitOfWork, int]:
    uow = InMemoryUnitOfWork()
    app = uow.applications.add(Application(name="Shop", github_repository=repository))
    assert app.id is not None
    return uow, app.id


def test_starts_sync_with_the_requested_options() -> None:
    uow, app_id = _uow()
    runner = FakeSyncRunner()

    StartGitHubSync(uow, FakeIssueTracker(), runner).execute(app_id, True, Severity.HOCH)

    assert runner.requests == [SyncRequest(app_id, create_issues=True, min_level=Severity.HOCH)]


def test_without_repository_is_a_conflict() -> None:
    uow, app_id = _uow(repository=None)

    with pytest.raises(ConflictError, match="kein GitHub-Repository"):
        StartGitHubSync(uow, FakeIssueTracker(), FakeSyncRunner()).execute(app_id, False, None)


def test_without_configuration_is_an_issue_tracker_error() -> None:
    uow, app_id = _uow()

    with pytest.raises(IssueTrackerError, match="nicht konfiguriert"):
        StartGitHubSync(uow, FakeIssueTracker(configured=False), FakeSyncRunner()).execute(
            app_id, False, None
        )


def test_busy_runner_is_a_conflict() -> None:
    uow, app_id = _uow()

    with pytest.raises(ConflictError, match="läuft bereits"):
        StartGitHubSync(uow, FakeIssueTracker(), FakeSyncRunner(busy=True)).execute(
            app_id, False, None
        )
