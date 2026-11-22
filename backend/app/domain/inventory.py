"""Inventar-Domäne: Anwendungen und ihre manuell gepflegten Komponenten."""

import re
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum

from app.domain.vulnerability import Severity

COMPONENT_NAME_MAX_LENGTH = 200
COMPONENT_VERSION_MAX_LENGTH = 100
_GITHUB_REPOSITORY_RE = re.compile(r"^([A-Za-z0-9-]{1,39})/([A-Za-z0-9._-]{1,100})$")
_RESERVED_REPOSITORY_NAMES = frozenset({".", ".."})


def is_valid_github_repository(value: str) -> bool:
    """``owner/repo`` streng geprüft; keine Pfadtricks wie ``..`` in API-URLs."""
    match = _GITHUB_REPOSITORY_RE.fullmatch(value)
    return match is not None and match.group(2) not in _RESERVED_REPOSITORY_NAMES


class Category(StrEnum):
    """Art einer Komponente."""

    LANGUAGE = "language"
    FRAMEWORK = "framework"
    LIBRARY = "library"
    SERVICE = "service"


class Ecosystem(StrEnum):
    """Paket-Ökosystem für das versionsgenaue OSV-Matching."""

    NPM = "npm"
    PYPI = "PyPI"
    GO = "Go"
    CRATES_IO = "crates.io"
    RUBYGEMS = "RubyGems"
    PACKAGIST = "Packagist"
    MAVEN = "Maven"
    NUGET = "NuGet"
    HACKAGE = "Hackage"
    CRAN = "CRAN"
    OPAM = "opam"


@dataclass(frozen=True)
class Component:
    """Eine Position im Inventar. ``ecosystem`` None → Produkt/CPE-Matching.

    ``sbom_id`` None → manuell gepflegt. ``checked`` False → wird nicht abgeglichen.
    ``retired_in_version_id`` gesetzt → ausgebaut, nicht mehr im Scan.
    """

    name: str
    version: str
    category: Category
    ecosystem: Ecosystem | None
    direct: bool
    id: int | None = None
    application_id: int | None = None
    sbom_id: int | None = None
    checked: bool = True
    retired_in_version_id: int | None = None

    @property
    def is_retired(self) -> bool:
        """Mit einer SBOM-Version ausgebaut; Treffer warten auf die Auflösung im Scan."""
        return self.retired_in_version_id is not None


@dataclass
class Application:
    """Eine manuell gepflegte Anwendung mit ihren Komponenten."""

    name: str
    description: str = ""
    id: int | None = None
    components: list[Component] = field(default_factory=list)
    github_repository: str | None = None
    auto_issue_min_level: Severity | None = None
    auto_issue_enabled_at: datetime | None = None
    github_synced_at: datetime | None = None
    github_sync_message: str = ""
    inventory_changed_at: datetime | None = None

    def mark_inventory_changed(self, now: datetime) -> "Application":
        """Kopie mit neuem Änderungszeitpunkt des Inventars (Komponenten, SBOMs)."""
        return replace(self, inventory_changed_at=now)
