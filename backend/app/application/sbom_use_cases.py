"""Use Cases zum Hinterlegen von SBOMs an einer Anwendung."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime

from app.application.inventory_use_cases import mark_inventory_changed
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
from app.domain.vulnerability import Finding, FindingStatus, ResolutionSource

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


def _remove_components(uow: UnitOfWork, components: Sequence[Component]) -> None:
    """Entfernt SBOM-Komponenten samt ihrer Treffer (Treffer zuerst wegen Fremdschlüssel)."""
    ids = [component.id for component in components if component.id is not None]
    uow.findings.delete_for_components(ids)
    uow.components.delete_many(ids)


def _is_unchanged(component: Component, entry: SbomEntry) -> bool:
    return (component.category, component.direct, component.checked) == (
        entry.category,
        entry.direct,
        entry.checked,
    )


def _is_reported_fix(finding: Finding) -> bool:
    return (
        finding.status == FindingStatus.FIXED and finding.resolved_by == ResolutionSource.REPORTED
    )


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
        live = [
            component
            for component in self._uow.components.list_for_sbom(sbom.id)
            if not component.is_retired
        ]
        changes = reconcile(live, entries)
        self._apply(application_id, version, changes)
        mark_inventory_changed(self._uow, application_id, now)
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

    def _apply(self, application_id: int, version: SbomVersion, changes: Reconciliation) -> None:
        assert version.id is not None
        for component, entry in changes.to_keep:
            if _is_unchanged(component, entry):
                continue
            self._uow.components.update(
                replace(
                    component, category=entry.category, direct=entry.direct, checked=entry.checked
                )
            )
        self._reopen_reported_fixes([component for component, _ in changes.to_keep], version)
        self._retire_or_remove(changes.to_remove, version.id)
        self._uow.components.add_many(
            application_id,
            [_component_from(entry, version.sbom_id) for entry in changes.to_add],
        )

    def _reopen_reported_fixes(self, kept: Sequence[Component], version: SbomVersion) -> None:
        """Gemeldetes „behoben“ gilt erst, wenn die Komponente nicht mehr ausgeliefert wird."""
        by_id = {component.id: component for component in kept if component.id is not None}
        reported = [
            finding
            for finding in self._uow.findings.list_for_components(list(by_id))
            if _is_reported_fix(finding)
        ]
        if not reported:
            return
        sbom_name = self._uow.sboms.get(version.sbom_id).name
        for finding in reported:
            component = by_id[finding.component_id]
            note = (
                f"Wieder offen: {component.name} {component.version} weiterhin in "
                f"SBOM {sbom_name} {version.label} enthalten."
            )
            self._uow.findings.save_report(finding.reopened().with_note(note))

    def _retire_or_remove(self, components: Sequence[Component], version_id: int) -> None:
        """Mit Treffern: ausbauen (der nächste Scan löst auf); ohne: löschen."""
        ids = [component.id for component in components if component.id is not None]
        with_findings = self._uow.findings.components_with_findings(ids)
        self._uow.components.retire_many(
            [component_id for component_id in ids if component_id in with_findings], version_id
        )
        self._uow.components.delete_many(
            [component_id for component_id in ids if component_id not in with_findings]
        )


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
    def __init__(self, uow: UnitOfWork, clock: Callable[[], datetime]) -> None:
        self._uow = uow
        self._clock = clock

    def execute(self, *, application_id: int, sbom_id: int) -> None:
        _owned_sbom(self._uow, application_id, sbom_id)
        _remove_components(self._uow, self._uow.components.list_for_sbom(sbom_id))
        self._uow.sboms.delete(sbom_id)
        mark_inventory_changed(self._uow, application_id, self._clock())
        self._uow.commit()
