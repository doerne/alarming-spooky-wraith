"""Quellen-Domäne: welche CVE-Quellen es gibt und wie sie eingestellt sind.

Die Quellen selbst entstehen im Code (Registry); die Datenbank hält nur die
Einstellungen pro Quelle (aktiv, API-Key, Ergebnis des letzten Laufs).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SourceKind(StrEnum):
    """Wie eine Quelle ihre Daten liefert."""

    PACKAGE_QUERY = "package_query"
    BULK = "bulk"


class MatchScope(StrEnum):
    """Welche Komponenten eine Quelle abgleicht."""

    PACKAGE = "package"
    PRODUCT = "product"
    NAME = "name"


class ApiKeyRequirement(StrEnum):
    NONE = "none"
    OPTIONAL = "optional"
    REQUIRED = "required"


class SourceStatus(StrEnum):
    """Abgeleiteter Zustand für Oberfläche und Ingest."""

    DISABLED = "disabled"
    MISSING_KEY = "missing_key"
    READY = "ready"


class RunStatus(StrEnum):
    """Ergebnis des letzten Ingest-Laufs einer Quelle."""

    RUNNING = "running"
    OK = "ok"
    ERROR = "error"
    SKIPPED = "skipped"


# Feste Rangfolge beim Zusammenführen abweichender Werte (Spec §7).
MERGE_PRECEDENCE: tuple[str, ...] = ("nvd", "osv", "ghsa", "euvd", "cve-org")


@dataclass(frozen=True)
class SourceDescriptor:
    """Beschreibt eine im Code eingebaute Quelle."""

    key: str
    name: str
    homepage_url: str
    description: str
    kind: SourceKind
    scope: MatchScope
    api_key_requirement: ApiKeyRequirement = ApiKeyRequirement.NONE
    api_key_hint: str = ""
    ecosystems: frozenset[str] = frozenset()


@dataclass
class SourceSetting:
    """Gespeicherte Einstellung einer Quelle. Fehlt sie, gelten diese Defaults."""

    source_key: str
    enabled: bool = True
    api_key: str | None = None
    last_run_at: datetime | None = None
    last_status: RunStatus | None = None
    last_message: str = ""
    last_findings: int | None = None


def source_status(descriptor: SourceDescriptor, setting: SourceSetting) -> SourceStatus:
    if not setting.enabled:
        return SourceStatus.DISABLED
    if descriptor.api_key_requirement == ApiKeyRequirement.REQUIRED and not setting.api_key:
        return SourceStatus.MISSING_KEY
    return SourceStatus.READY
