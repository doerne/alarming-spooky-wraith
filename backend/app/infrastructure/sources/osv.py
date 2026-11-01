"""OSV.dev: versionsgenaue Abfrage pro Paket (POST /v1/query)."""

import httpx

from app.domain.inventory import Component
from app.domain.ports import SourceVuln
from app.domain.sources import MatchScope, SourceDescriptor, SourceKind
from app.infrastructure.sources.http_errors import get_json
from app.infrastructure.sources.osv_format import parse_osv_record

DESCRIPTOR = SourceDescriptor(
    key="osv",
    name="OSV.dev",
    homepage_url="https://osv.dev",
    description="Open Source Vulnerabilities von Google; versionsgenau pro Paket, "
    "über 20 Ökosysteme.",
    kind=SourceKind.PACKAGE_QUERY,
    scope=MatchScope.PACKAGE,
)


class OsvSource:
    descriptor = DESCRIPTOR

    def __init__(self, base_url: str, client: httpx.Client) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client

    def query(self, component: Component, api_key: str | None) -> list[SourceVuln]:  # noqa: ARG002 - OSV braucht keinen Key
        assert component.ecosystem is not None
        payload = {
            "version": component.version,
            "package": {"ecosystem": component.ecosystem.value, "name": component.name},
        }
        data = get_json(self._client, "POST", f"{self._base_url}/v1/query", json=payload)
        return [parse_osv_record(raw, "osv") for raw in data.get("vulns", [])]
