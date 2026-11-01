"""Package-URLs (purl) für Quellen, die Pakete per purl abfragen."""

from urllib.parse import quote

from app.domain.inventory import Component, Ecosystem
from app.infrastructure.sources.names import normalize_pypi

_PURL_TYPE: dict[Ecosystem, str] = {
    Ecosystem.NPM: "npm",
    Ecosystem.PYPI: "pypi",
    Ecosystem.MAVEN: "maven",
    Ecosystem.RUBYGEMS: "gem",
    Ecosystem.GO: "golang",
    Ecosystem.CRATES_IO: "cargo",
    Ecosystem.NUGET: "nuget",
    Ecosystem.PACKAGIST: "composer",
    Ecosystem.CRAN: "cran",
}

PURL_ECOSYSTEMS = frozenset(ecosystem.value for ecosystem in _PURL_TYPE)


def _name_path(ecosystem: Ecosystem, name: str) -> str:
    if ecosystem == Ecosystem.MAVEN:
        return "/".join(quote(part, safe="") for part in name.split(":", 1))
    if ecosystem == Ecosystem.PYPI:
        name = normalize_pypi(name)
    return "/".join(quote(part, safe="") for part in name.split("/"))


def package_url(component: Component) -> str | None:
    ecosystem = component.ecosystem
    if ecosystem is None or ecosystem not in _PURL_TYPE:
        return None
    version = quote(component.version, safe="")
    return f"pkg:{_PURL_TYPE[ecosystem]}/{_name_path(ecosystem, component.name)}@{version}"
