"""Snyk Vulnerability DB: ``GET /rest/orgs/{org}/packages/{purl}/issues``.

Braucht Org-ID und Token. Die Nutzungsbedingungen von Snyk vor dem
Aktivieren prüfen.
"""

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

import httpx

from app.domain.inventory import Component
from app.domain.ports import SourceVuln
from app.domain.sources import ApiKeyRequirement, MatchScope, SourceDescriptor, SourceKind
from app.infrastructure.sources.http_errors import get_json
from app.infrastructure.sources.names import split_key
from app.infrastructure.sources.purl import PURL_ECOSYSTEMS, package_url

_KEY_FORMAT = "<org-id>:<token>"
_API_VERSION = "2024-06-26"

DESCRIPTOR = SourceDescriptor(
    key="snyk",
    name="Snyk Vulnerability DB",
    homepage_url="https://security.snyk.io",
    description="Snyk-Schwachstellendatenbank, gut nach Sprache/Paket. "
    "Nutzungsbedingungen von Snyk prüfen, bevor die Quelle aktiviert wird.",
    kind=SourceKind.PACKAGE_QUERY,
    scope=MatchScope.PACKAGE,
    api_key_requirement=ApiKeyRequirement.REQUIRED,
    api_key_hint=f"Format {_KEY_FORMAT}",
    ecosystems=PURL_ECOSYSTEMS,
)


def _to_vuln(item: Mapping[str, Any]) -> SourceVuln:
    attributes = item.get("attributes") or {}
    issue_id = str(attributes.get("key") or item["id"])
    problems = attributes.get("problems") or []
    scores = [s["score"] for s in attributes.get("severities") or [] if s.get("score")]
    return SourceVuln(
        source_key="snyk",
        id=issue_id,
        aliases=[p["id"] for p in problems if p.get("source") == "CVE"],
        summary=attributes.get("title") or "",
        details=attributes.get("description") or "",
        cvss_base=float(scores[0]) if scores else None,
        fixed_version=None,
        references=[],
        url=f"https://security.snyk.io/vuln/{issue_id}",
    )


class SnykSource:
    descriptor = DESCRIPTOR

    def __init__(self, client: httpx.Client, base_url: str = "https://api.snyk.io") -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    def query(self, component: Component, api_key: str | None) -> list[SourceVuln]:
        org_id, token = split_key(api_key, _KEY_FORMAT)
        purl = package_url(component)
        if purl is None:
            return []
        org_path = quote(org_id, safe="")
        url = f"{self._base_url}/rest/orgs/{org_path}/packages/{quote(purl, safe='')}/issues"
        data = get_json(
            self._client,
            "GET",
            url,
            params={"version": _API_VERSION},
            headers={"Authorization": f"token {token}"},
            not_found_is_empty=True,
        )
        return [_to_vuln(item) for item in (data or {}).get("data") or []]
