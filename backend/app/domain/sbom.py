"""SBOM-Domäne: benannte Stücklisten einer Anwendung und ihre Versionen."""

from dataclasses import dataclass
from datetime import datetime

from app.domain.inventory import Category, Ecosystem

SBOM_NAME_MAX_LENGTH = 100
SBOM_LABEL_MAX_LENGTH = 100
SBOM_SERIAL_MAX_LENGTH = 100
SBOM_MAX_COMPONENTS = 50_000


@dataclass(frozen=True)
class SbomEntry:
    """Eine Komponente, wie sie in einer SBOM-Version steht."""

    name: str
    version: str
    category: Category
    ecosystem: Ecosystem | None
    direct: bool
    purl: str | None

    @property
    def checked(self) -> bool:
        """Nur Einträge mit bekanntem Ökosystem werden abgeglichen."""
        return self.ecosystem is not None


@dataclass(frozen=True)
class ParsedSbom:
    """Ergebnis des Einlesens einer SBOM-Datei."""

    entries: tuple[SbomEntry, ...]
    serial_number: str | None
    suggested_label: str | None
    skipped: int


@dataclass
class Sbom:
    """Eine benannte Stückliste einer Anwendung, z. B. „backend-image“."""

    application_id: int
    name: str
    id: int | None = None


@dataclass(frozen=True)
class SbomVersion:
    """Ein Upload einer SBOM. Nur die aktuelle Version wird abgeglichen."""

    sbom_id: int
    label: str
    uploaded_at: datetime
    serial_number: str | None
    is_current: bool
    entries: tuple[SbomEntry, ...]
    id: int | None = None

    @property
    def component_count(self) -> int:
        return len(self.entries)

    @property
    def unchecked_count(self) -> int:
        return sum(1 for entry in self.entries if not entry.checked)
