from datetime import UTC, datetime

import pytest

from app.application.github_settings import GitHubSettingsChange, UpdateGitHubSettings
from app.domain.errors import InvalidValueError
from app.domain.inventory import Application, is_valid_github_repository
from app.domain.vulnerability import Severity
from tests.fakes import InMemoryUnitOfWork

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("value", "valid"),
    [
        ("acme/shop", True),
        ("acme/shop.web-2_x", True),
        ("acme\nx/shop", False),
        ("../shop", False),
        ("acme/..", False),
        ("acme/.", False),
        ("acme", False),
        ("acme/shop/extra", False),
        ("a" * 40 + "/shop", False),
    ],
)
def test_repository_must_be_owner_slash_repo(value: str, valid: bool) -> None:
    assert is_valid_github_repository(value) is valid


def _uow_with_app() -> tuple[InMemoryUnitOfWork, int]:
    uow = InMemoryUnitOfWork()
    app = uow.applications.add(Application(name="Shop"))
    assert app.id is not None
    return uow, app.id


def test_setting_repository_and_threshold_stores_them() -> None:
    uow, app_id = _uow_with_app()
    change = GitHubSettingsChange(
        repository="acme/shop",
        min_level=Severity.HOCH,
        set_repository=True,
        set_min_level=True,
    )

    UpdateGitHubSettings(uow, lambda: NOW).execute(app_id, change)

    stored = uow.applications.get(app_id)
    assert stored.github_repository == "acme/shop"
    assert stored.auto_issue_min_level == Severity.HOCH
    assert stored.auto_issue_enabled_at == NOW
    assert uow.commits == 1


def test_changing_threshold_restarts_enable_time_but_unrelated_change_keeps_it() -> None:
    uow, app_id = _uow_with_app()
    earlier = datetime(2026, 1, 1, tzinfo=UTC)
    app = uow.applications.get(app_id)
    app.auto_issue_min_level = Severity.HOCH
    app.auto_issue_enabled_at = earlier

    UpdateGitHubSettings(uow, lambda: NOW).execute(
        app_id, GitHubSettingsChange(repository="acme/shop", set_repository=True)
    )
    assert uow.applications.get(app_id).auto_issue_enabled_at == earlier

    UpdateGitHubSettings(uow, lambda: NOW).execute(
        app_id, GitHubSettingsChange(min_level=Severity.KRITISCH, set_min_level=True)
    )
    assert uow.applications.get(app_id).auto_issue_enabled_at == NOW


def test_switching_automation_off_clears_enable_time() -> None:
    uow, app_id = _uow_with_app()
    app = uow.applications.get(app_id)
    app.auto_issue_min_level = Severity.HOCH
    app.auto_issue_enabled_at = NOW

    UpdateGitHubSettings(uow, lambda: NOW).execute(app_id, GitHubSettingsChange(set_min_level=True))

    stored = uow.applications.get(app_id)
    assert stored.auto_issue_min_level is None
    assert stored.auto_issue_enabled_at is None


def test_invalid_repository_is_rejected_and_nothing_changes() -> None:
    uow, app_id = _uow_with_app()

    with pytest.raises(InvalidValueError):
        UpdateGitHubSettings(uow, lambda: NOW).execute(
            app_id, GitHubSettingsChange(repository="acme/../x", set_repository=True)
        )
    assert uow.applications.get(app_id).github_repository is None
