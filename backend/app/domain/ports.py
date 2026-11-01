"""Repository- und Datenquellen-Ports (Protocols). Keine Infrastruktur."""

from dataclasses import dataclass
from typing import Protocol

from app.domain.inventory import Application, Component
from app.domain.sources import SourceDescriptor, SourceSetting
from app.domain.vulnerability import Advisory, Finding


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


class FindingRepository(Protocol):
    def upsert(self, finding: Finding) -> Finding: ...
    def list(self) -> list[Finding]: ...


class AdvisoryRepository(Protocol):
    def upsert(self, advisory: Advisory) -> Advisory: ...
    def get(self, advisory_id: str) -> Advisory: ...


@dataclass(frozen=True)
class SourceReference:
    """Beleg, welche Quelle eine Advisory geliefert hat."""

    source_key: str
    url: str


class AdvisoryStore(Protocol):
    """Legt Advisories als OKF-Files ab und liest sie wieder."""

    def save(
        self, advisory: Advisory, *, tags: list[str], sources: list[SourceReference], body: str
    ) -> str: ...
    def read(self, advisory_id: str) -> str: ...


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
    def load(self, api_key: str | None) -> list[SourceVuln]: ...


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


class OsvClient(Protocol):
    """Übergang bis Task 16: wird durch PackageQuerySource ersetzt."""

    def query(self, ecosystem: str, name: str, version: str) -> list[SourceVuln]: ...
