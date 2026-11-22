from app.application.github_sync import GitHubSyncServices, SyncRequest, run_github_sync
from tests.fakes import (
    FakeAdvisoryStore,
    FakeIssueFormatter,
    FakeIssueTracker,
    InMemoryUnitOfWork,
    fixed_clock,
    uow_factory_for,
)

_REQUEST = SyncRequest(None, create_issues=False, min_level=None)


def _services(*, configured: bool) -> GitHubSyncServices:
    tracker = FakeIssueTracker(configured=configured)
    return GitHubSyncServices(tracker, FakeIssueFormatter(), FakeAdvisoryStore(), fixed_clock)


def test_sync_without_configuration_reports_false() -> None:
    factory = uow_factory_for(InMemoryUnitOfWork())
    assert run_github_sync(factory, _services(configured=False), _REQUEST) is False


def test_configured_sync_reports_true() -> None:
    factory = uow_factory_for(InMemoryUnitOfWork())
    assert run_github_sync(factory, _services(configured=True), _REQUEST) is True
