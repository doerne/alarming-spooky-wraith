import pytest

from app.application.source_registry import SourceRegistry
from app.application.source_use_cases import (
    ListSources,
    RemoveSourceApiKey,
    ResetInterruptedRuns,
    SetSourceApiKey,
    SetSourceEnabled,
)
from app.domain.errors import EntityNotFoundError
from app.domain.sources import ApiKeyRequirement, RunStatus, SourceSetting, SourceStatus
from tests.fakes import FakeBulkSource, FakePackageSource, InMemoryUnitOfWork, descriptor


def _registry() -> SourceRegistry:
    return SourceRegistry(
        [
            FakePackageSource(descriptor("osv")),
            FakePackageSource(descriptor("snyk", requirement=ApiKeyRequirement.REQUIRED)),
        ]
    )


def test_list_uses_defaults_without_setting(uow: InMemoryUnitOfWork) -> None:
    views = ListSources(uow, _registry()).execute()
    assert [view.descriptor.key for view in views] == ["osv", "snyk"]
    assert views[0].setting.enabled is True
    assert views[0].status == SourceStatus.READY
    assert views[1].status == SourceStatus.MISSING_KEY


def test_list_ignores_settings_of_removed_sources(uow: InMemoryUnitOfWork) -> None:
    uow.source_settings.save(SourceSetting(source_key="gone"))
    views = ListSources(uow, _registry()).execute()
    assert "gone" not in [view.descriptor.key for view in views]


def test_disable_source_persists_and_commits(uow: InMemoryUnitOfWork) -> None:
    view = SetSourceEnabled(uow, _registry()).execute("osv", enabled=False)
    assert view.status == SourceStatus.DISABLED
    stored = uow.source_settings.get("osv")
    assert stored is not None
    assert stored.enabled is False
    assert uow.commits == 1


def test_set_api_key_trims_and_stores(uow: InMemoryUnitOfWork) -> None:
    view = SetSourceApiKey(uow, _registry()).execute("snyk", "  org:token  ")
    assert view.has_api_key is True
    assert view.status == SourceStatus.READY
    stored = uow.source_settings.get("snyk")
    assert stored is not None
    assert stored.api_key == "org:token"
    assert uow.commits == 1


def test_set_blank_api_key_raises(uow: InMemoryUnitOfWork) -> None:
    with pytest.raises(ValueError, match="API-Key darf nicht leer sein"):
        SetSourceApiKey(uow, _registry()).execute("snyk", "   ")
    assert uow.source_settings.get("snyk") is None


def test_remove_api_key_makes_required_source_missing_key(uow: InMemoryUnitOfWork) -> None:
    SetSourceApiKey(uow, _registry()).execute("snyk", "org:token")
    view = RemoveSourceApiKey(uow, _registry()).execute("snyk")
    assert view.has_api_key is False
    assert view.status == SourceStatus.MISSING_KEY


def test_unknown_source_raises_not_found(uow: InMemoryUnitOfWork) -> None:
    with pytest.raises(EntityNotFoundError):
        SetSourceEnabled(uow, _registry()).execute("nope", enabled=True)


def test_registry_rejects_duplicate_keys() -> None:
    with pytest.raises(ValueError, match="osv"):
        SourceRegistry([FakePackageSource(descriptor("osv")), FakeBulkSource(descriptor("osv"))])


def test_reset_interrupted_runs(uow: InMemoryUnitOfWork) -> None:
    uow.source_settings.save(SourceSetting(source_key="osv", last_status=RunStatus.RUNNING))
    uow.source_settings.save(SourceSetting(source_key="ghsa", last_status=RunStatus.OK))
    assert ResetInterruptedRuns(uow).execute() == 1
    osv = uow.source_settings.get("osv")
    ghsa = uow.source_settings.get("ghsa")
    assert osv is not None
    assert osv.last_status == RunStatus.ERROR
    assert osv.last_message == "Lauf abgebrochen"
    assert ghsa is not None
    assert ghsa.last_status == RunStatus.OK
    assert uow.commits == 1
