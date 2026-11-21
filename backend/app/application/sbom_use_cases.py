"""Use Cases zum Hinterlegen von SBOMs an einer Anwendung."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime

from app.application.sbom_reconcile import Reconciliation, merge_duplicates, reconcile
from app.application.unit_of_work import UnitOfWork
from app.domain.errors import DuplicateSbomVersionError, EntityNotFoundError, InvalidValueError
from app.domain.inventory import Component
from app.domain.ports import SbomParser
from app.domain.sbom import (
    SBOM_LABEL_MAX_LENGTH,
    SBOM_NAME_MAX_LENGTH,
    ParsedSbom,
    Sbom,
    SbomEntry,
    SbomVersion,
)

_CLOCK_LABEL_FORMAT = "%Y-%m-%d %H:%M"


@dataclass(frozen=True)
class SbomUploadResult:
    sbom: Sbom
    version: SbomVersion
    added: int
    removed: int
    kept: int
    unchecked: int
    skipped: int


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned or len(cleaned) > SBOM_NAME_MAX_LENGTH:
        raise InvalidValueError(f"SBOM-Name muss 1 bis {SBOM_NAME_MAX_LENGTH} Zeichen haben")
    return cleaned


def _label(label: str | None, parsed: ParsedSbom, now: datetime) -> str:
    chosen = (label or "").strip() or parsed.suggested_label
    return (chosen or now.strftime(_CLOCK_LABEL_FORMAT))[:SBOM_LABEL_MAX_LENGTH]


def _remove_component(uow: UnitOfWork, component: Component) -> None:
    """Entfernt eine SBOM-Komponente samt ihrer Treffer."""
    assert component.id is not None
    uow.findings.delete_for_component(component.id)
    uow.components.delete(component.id)


def _component_from(entry: SbomEntry, sbom_id: int) -> Component:
    return Component(
        name=entry.name,
        version=entry.version,
        category=entry.category,
        ecosystem=entry.ecosystem,
        direct=entry.direct,
        sbom_id=sbom_id,
        checked=entry.checked,
    )


class UploadSbomVersion:
    def __init__(self, uow: UnitOfWork, parser: SbomParser, clock: Callable[[], datetime]) -> None:
        self._uow = uow
        self._parser = parser
        self._clock = clock

    def execute(
        self,
        *,
        application_id: int,
        name: str,
        label: str | None,
        document: Mapping[str, object],
    ) -> SbomUploadResult:
        self._uow.applications.get(application_id)  # EntityNotFoundError, falls unbekannt
        cleaned_name = _clean_name(name)
        parsed = self._parser.parse(document)
        entries = merge_duplicates(parsed.entries)
        sbom = self._resolve_sbom(application_id, cleaned_name, parsed.serial_number)
        assert sbom.id is not None
        now = self._clock()
        version = self._store_version(
            SbomVersion(
                sbom_id=sbom.id,
                label=_label(label, parsed, now),
                uploaded_at=now,
                serial_number=parsed.serial_number,
                is_current=True,
                entries=entries,
            )
        )
        changes = reconcile(self._uow.components.list_for_sbom(sbom.id), entries)
        self._apply(application_id, sbom.id, changes)
        self._uow.commit()
        return SbomUploadResult(
            sbom=sbom,
            version=version,
            added=len(changes.to_add),
            removed=len(changes.to_remove),
            kept=len(changes.to_keep),
            unchecked=version.unchecked_count,
            skipped=parsed.skipped,
        )

    def _resolve_sbom(self, application_id: int, name: str, serial_number: str | None) -> Sbom:
        existing = self._uow.sboms.find_by_name(application_id, name)
        if existing is None:
            return self._uow.sboms.add(Sbom(application_id=application_id, name=name))
        assert existing.id is not None
        current = self._uow.sbom_versions.current_for_sbom(existing.id)
        if serial_number and current and current.serial_number == serial_number:
            raise DuplicateSbomVersionError(serial_number)
        return existing

    def _store_version(self, version: SbomVersion) -> SbomVersion:
        """Archiviert die bisherige aktuelle Version und legt die neue an."""
        current = self._uow.sbom_versions.current_for_sbom(version.sbom_id)
        if current is not None and current.id is not None:
            self._uow.sbom_versions.archive(current.id)
        return self._uow.sbom_versions.add(version)

    def _apply(self, application_id: int, sbom_id: int, changes: Reconciliation) -> None:
        for component, entry in changes.to_keep:
            self._uow.components.update(
                replace(
                    component, category=entry.category, direct=entry.direct, checked=entry.checked
                )
            )
        for component in changes.to_remove:
            _remove_component(self._uow, component)
        for entry in changes.to_add:
            self._uow.components.add(application_id, _component_from(entry, sbom_id))


@dataclass(frozen=True)
class SbomOverview:
    sbom: Sbom
    current: SbomVersion | None
    version_count: int


def _owned_sbom(uow: UnitOfWork, application_id: int, sbom_id: int) -> Sbom:
    """SBOM, die zur Anwendung gehört; sonst EntityNotFoundError."""
    uow.applications.get(application_id)
    sbom = uow.sboms.get(sbom_id)
    if sbom.application_id != application_id:
        raise EntityNotFoundError("SBOM", sbom_id)
    return sbom


class ListSboms:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, application_id: int) -> list[SbomOverview]:
        self._uow.applications.get(application_id)  # EntityNotFoundError, falls unbekannt
        sboms = sorted(
            self._uow.sboms.list_for_application(application_id), key=lambda sbom: sbom.name
        )
        return [self._overview(sbom) for sbom in sboms]

    def _overview(self, sbom: Sbom) -> SbomOverview:
        assert sbom.id is not None
        versions = self._uow.sbom_versions.list_for_sbom(sbom.id)
        current = next((version for version in versions if version.is_current), None)
        return SbomOverview(sbom=sbom, current=current, version_count=len(versions))


class ListSbomVersions:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, *, application_id: int, sbom_id: int) -> list[SbomVersion]:
        _owned_sbom(self._uow, application_id, sbom_id)
        return self._uow.sbom_versions.list_for_sbom(sbom_id)


class GetSbomVersion:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, *, application_id: int, sbom_id: int, version_id: int) -> SbomVersion:
        _owned_sbom(self._uow, application_id, sbom_id)
        version = self._uow.sbom_versions.get(version_id)
        if version.sbom_id != sbom_id:
            raise EntityNotFoundError("SBOM-Version", version_id)
        return version


class DeleteSbom:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, *, application_id: int, sbom_id: int) -> None:
        _owned_sbom(self._uow, application_id, sbom_id)
        for component in self._uow.components.list_for_sbom(sbom_id):
            _remove_component(self._uow, component)
        self._uow.sboms.delete(sbom_id)
        self._uow.commit()
