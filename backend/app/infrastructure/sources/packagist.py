"""FriendsOfPHP / Packagist Security Advisories über die Packagist-API.

Die API liefert alle Advisories eines Pakets; die Version gleicht diese
Quelle selbst ab (Composer-Bedingungen in ``affectedVersions``).
"""

from collections.abc import Mapping
from typing import Any

import httpx

from app.domain.inventory import Component, Ecosystem
from app.domain.ports import AffectedPackage, RangeEvent, SourceVuln, VersionMatcher
from app.domain.sources import MatchScope, SourceDescriptor, SourceKind
from app.infrastructure.sources.constraints import parse_alternatives
from app.infrastructure.sources.http_errors import get_json

_PACKAGIST = Ecosystem.PACKAGIST.value

DESCRIPTOR = SourceDescriptor(
    key="packagist",
    name="FriendsOfPHP / Packagist",
    homepage_url="https://packagist.org/apidoc#list-security-advisories",
    description="Security-Advisories für PHP-Pakete (Composer), u. a. aus FriendsOfPHP.",
    kind=SourceKind.PACKAGE_QUERY,
    scope=MatchScope.PACKAGE,
    ecosystems=frozenset({_PACKAGIST}),
)


def composer_constraint_events(text: str) -> tuple[RangeEvent, ...]:
    return parse_alternatives(text, "|")[0]


def _to_vuln(advisory: Mapping[str, Any], package_name: str) -> SourceVuln:
    events, versions = parse_alternatives(advisory.get("affectedVersions") or "", "|")
    aliases = [alias for alias in (advisory.get("cve"), advisory.get("remoteId")) if alias]
    return SourceVuln(
        source_key="packagist",
        id=str(advisory["advisoryId"]),
        aliases=[str(alias) for alias in aliases],
        summary=advisory.get("title") or "",
        details="",
        cvss_base=None,
        fixed_version=None,
        references=[advisory["link"]] if advisory.get("link") else [],
        url=advisory.get("link") or "https://packagist.org",
        affected=(AffectedPackage(_PACKAGIST, package_name, events, versions),),
    )


class PackagistSource:
    descriptor = DESCRIPTOR

    def __init__(
        self,
        client: httpx.Client,
        versions: VersionMatcher,
        base_url: str = "https://packagist.org",
    ) -> None:
        self._client = client
        self._versions = versions
        self._base_url = base_url.rstrip("/")

    def query(self, component: Component, api_key: str | None) -> list[SourceVuln]:  # noqa: ARG002 - kein Key nötig
        url = f"{self._base_url}/api/security-advisories/"
        data = get_json(self._client, "GET", url, params={"packages[]": component.name})
        advisories = (data.get("advisories") or {}).get(component.name) or []
        vulns = [_to_vuln(advisory, component.name) for advisory in advisories]
        return [vuln for vuln in vulns if self._affects(component, vuln)]

    def _affects(self, component: Component, vuln: SourceVuln) -> bool:
        return any(
            self._versions.is_affected(_PACKAGIST, component.version, package)
            for package in vuln.affected
        )
