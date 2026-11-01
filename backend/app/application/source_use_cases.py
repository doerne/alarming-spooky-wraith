"""Use Cases zum Anzeigen und Einstellen der Quellen."""

from collections.abc import Callable
from dataclasses import dataclass, replace

from app.application.source_registry import SourceRegistry
from app.application.unit_of_work import UnitOfWork
from app.domain.sources import SourceDescriptor, SourceSetting, SourceStatus, source_status


@dataclass(frozen=True)
class SourceView:
    """Eine Quelle mit ihrer Einstellung und dem abgeleiteten Status."""

    descriptor: SourceDescriptor
    setting: SourceSetting
    status: SourceStatus

    @property
    def has_api_key(self) -> bool:
        return bool(self.setting.api_key)


def load_setting(uow: UnitOfWork, source_key: str) -> SourceSetting:
    """Gespeicherte Einstellung oder Defaults, wenn es noch keine gibt."""
    return uow.source_settings.get(source_key) or SourceSetting(source_key=source_key)


def _view(descriptor: SourceDescriptor, setting: SourceSetting) -> SourceView:
    return SourceView(descriptor, setting, source_status(descriptor, setting))


class ListSources:
    def __init__(self, uow: UnitOfWork, registry: SourceRegistry) -> None:
        self._uow = uow
        self._registry = registry

    def execute(self) -> list[SourceView]:
        stored = {setting.source_key: setting for setting in self._uow.source_settings.get_all()}
        return [
            _view(descriptor, stored.get(descriptor.key) or SourceSetting(descriptor.key))
            for descriptor in self._registry.descriptors()
        ]


class _ChangeSetting:
    """Gemeinsamer Ablauf: Quelle prüfen, Einstellung ändern, speichern, bestätigen."""

    def __init__(self, uow: UnitOfWork, registry: SourceRegistry) -> None:
        self._uow = uow
        self._registry = registry

    def _apply(self, key: str, change: Callable[[SourceSetting], SourceSetting]) -> SourceView:
        descriptor = self._registry.get(key).descriptor
        setting = change(load_setting(self._uow, key))
        self._uow.source_settings.save(setting)
        self._uow.commit()
        return _view(descriptor, setting)


class SetSourceEnabled(_ChangeSetting):
    def execute(self, key: str, enabled: bool) -> SourceView:
        return self._apply(key, lambda setting: replace(setting, enabled=enabled))


class SetSourceApiKey(_ChangeSetting):
    def execute(self, key: str, api_key: str) -> SourceView:
        trimmed = api_key.strip()
        if not trimmed:
            raise ValueError("API-Key darf nicht leer sein")
        return self._apply(key, lambda setting: replace(setting, api_key=trimmed))


class RemoveSourceApiKey(_ChangeSetting):
    def execute(self, key: str) -> SourceView:
        return self._apply(key, lambda setting: replace(setting, api_key=None))
