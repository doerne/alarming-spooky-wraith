"""Repository- und Datenquellen-Ports (Protocols). Keine Infrastruktur."""

from dataclasses import dataclass
from typing import Protocol

from app.domain.inventory import Application, Component
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


class AdvisoryStore(Protocol):
    """Legt Advisories als OKF-Files ab und liest sie wieder."""

    def save(self, advisory: Advisory, *, tags: list[str], source_url: str, body: str) -> str: ...
    def read(self, advisory_id: str) -> str: ...


@dataclass(frozen=True)
class OsvVuln:
    """Ein von OSV geliefertes Advisory, roh gemappt."""

    id: str
    aliases: list[str]
    summary: str
    details: str
    cvss_base: float | None
    fixed_version: str | None
    references: list[str]


class OsvClient(Protocol):
    def query(self, ecosystem: str, name: str, version: str) -> list[OsvVuln]: ...
