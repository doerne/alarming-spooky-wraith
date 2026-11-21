"""Repository- und Datenquellen-Ports (Protocols). Keine Infrastruktur."""

import builtins
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from app.domain.inventory import Application, Component
from app.domain.sbom import ParsedSbom, Sbom, SbomVersion
from app.domain.sources import SourceDescriptor, SourceSetting
from app.domain.vulnerability import (
    Advisory,
    Finding,
    FindingResolution,
    FindingStatus,
)


@dataclass(frozen=True)
class TrackedIssue:
    """Ein Issue beim Tracker, aus Sicht von CVE-Radar."""

    number: int
    url: str
    is_open: bool
    not_planned: bool = False  # geschlossen mit state_reason "not_planned"


@dataclass(frozen=True)
class IssueContent:
    """Inhalt eines anzulegenden Issues; ``marker`` identifiziert CVE und Anwendung."""

    title: str
    body: str
    labels: tuple[str, ...]
    marker: str


class IssueTracker(Protocol):
    def is_configured(self) -> bool: ...
    def existing_markers(self, repository: str) -> dict[str, TrackedIssue]:
        """Marker-Zeile → Issue für alle Issues mit Label `security` (alle Zustände)."""
        ...

    def get(self, repository: str, number: int) -> TrackedIssue | None:
        """None, wenn das Issue nicht (mehr) existiert."""
        ...

    def create(self, repository: str, content: IssueContent) -> TrackedIssue: ...
    def set_open(
        self, repository: str, number: int, is_open: bool, comment: str, not_planned: bool = False
    ) -> None: ...


class ApplicationRepository(Protocol):
    def add(self, application: Application) -> Application: ...
    def get(self, application_id: int) -> Application: ...
    def list(self) -> list[Application]: ...


class ComponentRepository(Protocol):
    def add(self, application_id: int, component: Component) -> Component: ...
    def get(self, component_id: int) -> Component: ...
    def update(self, component: Component) -> Component: ...
    def list_all(self) -> list[Component]: ...
    def list_for_application(self, application_id: int) -> list[Component]: ...
    def list_for_sbom(self, sbom_id: int) -> list[Component]: ...
    def add_many(self, application_id: int, components: Sequence[Component]) -> None: ...
    def delete_many(self, component_ids: Sequence[int]) -> None: ...
    def retire_many(self, component_ids: Sequence[int], version_id: int) -> None: ...


class FindingRepository(Protocol):
    def upsert(self, finding: Finding) -> Finding: ...
    def list(self) -> list[Finding]: ...
    def delete_for_components(self, component_ids: Sequence[int]) -> None: ...
    def list_for_advisory(self, advisory_id: str) -> builtins.list[Finding]: ...
    def components_with_findings(self, component_ids: Sequence[int]) -> set[int]: ...
    def list_for_components(self, component_ids: Sequence[int]) -> builtins.list[Finding]: ...
    def reassign(self, finding_id: int, advisory_id: str) -> None: ...
    def save_triage(self, finding_id: int, status: FindingStatus, comment: str) -> None: ...
    def resolve(self, finding_id: int, resolution: FindingResolution) -> None: ...
    def save_report(self, finding: Finding) -> None:
        """Übernimmt Status, Kommentar, Issue-URL und Auflösung des Treffers."""
        ...

    def delete(self, finding_id: int) -> None: ...


class SbomRepository(Protocol):
    def add(self, sbom: Sbom) -> Sbom: ...
    def get(self, sbom_id: int) -> Sbom: ...
    def find_by_name(self, application_id: int, name: str) -> Sbom | None: ...
    def list_for_application(self, application_id: int) -> list[Sbom]: ...
    def delete(self, sbom_id: int) -> None:
        """Löscht die SBOM samt aller Versionen. Ihre Komponenten müssen vorher entfernt sein."""
        ...


class SbomVersionRepository(Protocol):
    def add(self, version: SbomVersion) -> SbomVersion: ...
    def get(self, version_id: int) -> SbomVersion: ...
    def current_for_sbom(self, sbom_id: int) -> SbomVersion | None: ...
    def list_for_sbom(self, sbom_id: int) -> list[SbomVersion]:
        """Neueste Version zuerst."""
        ...

    def archive(self, version_id: int) -> None: ...


class SbomParser(Protocol):
    def parse(self, document: Mapping[str, object]) -> ParsedSbom: ...


class AdvisoryRepository(Protocol):
    def upsert(self, advisory: Advisory) -> Advisory: ...
    def get(self, advisory_id: str) -> Advisory: ...
    def find(self, advisory_id: str) -> Advisory | None: ...
    def delete(self, advisory_id: str) -> None: ...


class AdvisoryAliasRepository(Protocol):
    """Merkt sich frühere IDs zusammengeführter Advisories (alias → kanonisch)."""

    def save(self, alias_id: str, advisory_id: str) -> None: ...
    def resolve(self, alias_id: str) -> str | None: ...
    def remove(self, alias_id: str) -> None: ...
    def repoint(self, old_advisory_id: str, new_advisory_id: str) -> None:
        """Alle Aliase, die auf ``old_advisory_id`` zeigen, auf ``new_advisory_id`` umstellen."""
        ...


@dataclass(frozen=True)
class SourceReference:
    """Beleg, welche Quelle eine Advisory geliefert hat."""

    source_key: str
    url: str


@dataclass(frozen=True)
class AdvisoryDocument:
    """Inhalt eines OKF-Files, in Abschnitte zerlegt."""

    description: str
    rationale: str
    references: list[str]
    sources: list[SourceReference]


class AdvisoryStore(Protocol):
    """Legt Advisories als OKF-Files ab und liest sie wieder."""

    def save(
        self, advisory: Advisory, *, tags: list[str], sources: list[SourceReference], body: str
    ) -> str: ...
    def read(self, advisory_id: str) -> str: ...
    def read_document(self, advisory_id: str) -> AdvisoryDocument | None:
        """Zerlegtes Dokument; None, wenn es fehlt oder unlesbar ist."""
        ...

    def delete(self, advisory_id: str) -> None:
        """Entfernt das File; ein fehlendes File ist kein Fehler."""
        ...


@dataclass(frozen=True)
class RangeEvent:
    """Ein Ereignis eines OSV-Versionsbereichs (introduced/fixed/last_affected/limit)."""

    kind: str
    version: str


@dataclass(frozen=True)
class AffectedPackage:
    """Betroffenes Paket/Produkt mit Versionsbereichen oder expliziten Versionen."""

    ecosystem: str | None
    name: str
    events: tuple[RangeEvent, ...] = ()
    versions: tuple[str, ...] = ()


@dataclass(frozen=True)
class SourceVuln:
    """Eine von einer Quelle gelieferte Schwachstelle, einheitlich gemappt."""

    source_key: str
    id: str
    aliases: list[str]
    summary: str
    details: str
    cvss_base: float | None
    fixed_version: str | None
    references: list[str]
    url: str
    affected: tuple[AffectedPackage, ...] = ()


class PackageQuerySource(Protocol):
    """Quelle, die pro Komponente abgefragt wird."""

    @property
    def descriptor(self) -> SourceDescriptor: ...
    def query(self, component: Component, api_key: str | None) -> list[SourceVuln]: ...


class BulkSource(Protocol):
    """Quelle, die einmal pro Lauf einen Gesamtabzug liefert."""

    @property
    def descriptor(self) -> SourceDescriptor: ...
    def load(self, api_key: str | None, names: frozenset[str]) -> list[SourceVuln]:
        """Gesamtabzug; ``names`` (normalisierte Komponentennamen) darf früh filtern."""
        ...


VulnerabilitySource = PackageQuerySource | BulkSource


class SourceSettingRepository(Protocol):
    def get_all(self) -> list[SourceSetting]: ...
    def get(self, source_key: str) -> SourceSetting | None: ...
    def save(self, setting: SourceSetting) -> None: ...


class VersionMatcher(Protocol):
    """Prüft, ob eine Version in den Bereichen eines betroffenen Pakets liegt."""

    def is_affected(
        self, ecosystem: str | None, version: str, package: AffectedPackage
    ) -> bool: ...
