"""GitHub Advisory Database über die REST-API ``GET /advisories``.

``affects=<paket>@<version>`` lässt GitHub die Version selbst abgleichen.
Ein Token ist optional und hebt nur das Rate-Limit.
"""

from collections.abc import Mapping
from typing import Any

import httpx

from app.domain.inventory import Component, Ecosystem
from app.domain.ports import AffectedPackage, SourceVuln
from app.domain.sources import ApiKeyRequirement, MatchScope, SourceDescriptor, SourceKind
from app.infrastructure.sources.constraints import parse_constraint
from app.infrastructure.sources.http_errors import send

_GITHUB_ECOSYSTEM: dict[Ecosystem, str] = {
    Ecosystem.NPM: "npm",
    Ecosystem.PYPI: "pip",
    Ecosystem.MAVEN: "maven",
    Ecosystem.RUBYGEMS: "rubygems",
    Ecosystem.GO: "go",
    Ecosystem.CRATES_IO: "rust",
    Ecosystem.NUGET: "nuget",
    Ecosystem.PACKAGIST: "composer",
}
_MAX_PAGES = 10
_PAGE_SIZE = 100

DESCRIPTOR = SourceDescriptor(
    key="ghsa",
    name="GitHub Advisory Database",
    homepage_url="https://github.com/advisories",
    description="Von GitHub kuratierte Advisories (GHSA) für die großen Paket-Ökosysteme; "
    "deckt auch Angular, React und andere Framework-Repos ab.",
    kind=SourceKind.PACKAGE_QUERY,
    scope=MatchScope.PACKAGE,
    api_key_requirement=ApiKeyRequirement.OPTIONAL,
    api_key_hint="GitHub-Token (optional, hebt das Rate-Limit)",
    ecosystems=frozenset(ecosystem.value for ecosystem in _GITHUB_ECOSYSTEM),
)


def _cvss(advisory: Mapping[str, Any]) -> float | None:
    severities = advisory.get("cvss_severities") or {}
    for kind in ("cvss_v4", "cvss_v3"):
        score = (severities.get(kind) or {}).get("score")
        if score:
            return float(score)
    score = (advisory.get("cvss") or {}).get("score")
    return float(score) if score else None


def _affected(vulnerability: Mapping[str, Any]) -> AffectedPackage:
    package = vulnerability.get("package") or {}
    events, versions = parse_constraint(vulnerability.get("vulnerable_version_range") or "")
    return AffectedPackage(package.get("ecosystem"), package.get("name") or "", events, versions)


def _fixed_version(advisory: Mapping[str, Any]) -> str | None:
    for vulnerability in advisory.get("vulnerabilities") or []:
        patched = vulnerability.get("first_patched_version")
        if isinstance(patched, str):
            return patched
        if isinstance(patched, dict) and patched.get("identifier"):
            return str(patched["identifier"])
    return None


def parse_github_advisory(
    advisory: Mapping[str, Any], source_key: str, ecosystem: str
) -> SourceVuln:
    """GitHub-Advisory (global oder Repo) → SourceVuln; ``ecosystem`` im OSV-Namen."""
    cve = advisory.get("cve_id")
    affected = tuple(_affected(item) for item in advisory.get("vulnerabilities") or [])
    return SourceVuln(
        source_key=source_key,
        id=str(advisory["ghsa_id"]),
        aliases=[cve] if cve else [],
        summary=advisory.get("summary") or "",
        details=advisory.get("description") or "",
        cvss_base=_cvss(advisory),
        fixed_version=_fixed_version(advisory),
        references=[str(url) for url in advisory.get("references") or []],
        url=advisory.get("html_url") or "",
        affected=tuple(_with_ecosystem(package, ecosystem) for package in affected),
    )


def _with_ecosystem(package: AffectedPackage, ecosystem: str) -> AffectedPackage:
    """GitHub nennt Ökosysteme anders (pip, rust …) - auf OSV-Namen zurückführen."""
    return AffectedPackage(ecosystem, package.name, package.events, package.versions)


class GhsaSource:
    descriptor = DESCRIPTOR

    def __init__(self, client: httpx.Client, base_url: str = "https://api.github.com") -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    def query(self, component: Component, api_key: str | None) -> list[SourceVuln]:
        assert component.ecosystem is not None
        params: dict[str, str] | None = {
            "ecosystem": _GITHUB_ECOSYSTEM[component.ecosystem],
            "affects": f"{component.name}@{component.version}",
            "per_page": str(_PAGE_SIZE),
        }
        headers = {"Accept": "application/vnd.github+json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        url: str | None = f"{self._base_url}/advisories"
        vulns: list[SourceVuln] = []
        for _ in range(_MAX_PAGES):
            if url is None:
                break
            response = send(self._client, "GET", url, params=params, headers=headers)
            ecosystem = component.ecosystem.value
            vulns += [parse_github_advisory(item, "ghsa", ecosystem) for item in response.json()]
            url = response.links.get("next", {}).get("url")
            params = None  # die next-URL bringt ihre Query selbst mit
        return vulns
