"""Inventar-Domäne: Anwendungen und ihre manuell gepflegten Komponenten."""

from dataclasses import dataclass, field
from enum import StrEnum


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
    """Eine Position im Inventar. ``ecosystem`` None → Produkt/CPE-Matching."""

    name: str
    version: str
    category: Category
    ecosystem: Ecosystem | None
    direct: bool
    id: int | None = None
    application_id: int | None = None


@dataclass
class Application:
    """Eine manuell gepflegte Anwendung mit ihren Komponenten."""

    name: str
    description: str = ""
    id: int | None = None
    components: list[Component] = field(default_factory=list)
