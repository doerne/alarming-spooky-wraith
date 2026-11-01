"""Sonatype OSS Index: ``POST /api/v3/component-report`` mit purls.

Seit 2025 nur mit Token (HTTP Basic). Bei einem Sonatype-Guide-Token ist der
Benutzername beliebig.
"""

from collections.abc import Mapping
from typing import Any

import httpx

from app.domain.inventory import Component
from app.domain.ports import SourceVuln
from app.domain.sources import ApiKeyRequirement, MatchScope, SourceDescriptor, SourceKind
from app.infrastructure.sources.http_errors import get_json
from app.infrastructure.sources.names import split_key
from app.infrastructure.sources.purl import PURL_ECOSYSTEMS, package_url

_KEY_FORMAT = "<benutzer>:<token>"

DESCRIPTOR = SourceDescriptor(
    key="oss-index",
    name="Sonatype OSS Index",
    homepage_url="https://ossindex.sonatype.org",
    description="Schwachstellen-Index von Sonatype, besonders stark bei Java/Maven.",
    kind=SourceKind.PACKAGE_QUERY,
    scope=MatchScope.PACKAGE,
    api_key_requirement=ApiKeyRequirement.REQUIRED,
    api_key_hint=f"Format {_KEY_FORMAT} (bei Sonatype-Guide-Token ist der Benutzer beliebig)",
    ecosystems=PURL_ECOSYSTEMS,
)


def _to_vuln(item: Mapping[str, Any]) -> SourceVuln:
    cve = item.get("cve")
    reference = item.get("reference") or ""
    return SourceVuln(
        source_key="oss-index",
        id=str(item["id"]),
        aliases=[cve] if cve else [],
        summary=item.get("title") or "",
        details=item.get("description") or "",
        cvss_base=float(item["cvssScore"]) if item.get("cvssScore") else None,
        fixed_version=None,
        references=[reference, *(item.get("externalReferences") or [])] if reference else [],
        url=reference,
    )


class OssIndexSource:
    descriptor = DESCRIPTOR

    def __init__(
        self, client: httpx.Client, base_url: str = "https://ossindex.sonatype.org"
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    def query(self, component: Component, api_key: str | None) -> list[SourceVuln]:
        user, token = split_key(api_key, _KEY_FORMAT)
        purl = package_url(component)
        if purl is None:
            return []
        reports = get_json(
            self._client,
            "POST",
            f"{self._base_url}/api/v3/component-report",
            json={"coordinates": [purl]},
            auth=(user, token),
        )
        return [
            _to_vuln(item) for report in reports for item in report.get("vulnerabilities") or []
        ]
