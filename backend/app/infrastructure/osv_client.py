"""OSV.dev-Client (httpx). Mappt die API-Antwort auf SourceVuln.

Der CVSS-Basisscore wird aus dem Vektor der ``severity``-Eintraege berechnet.
"""

from typing import Any

import httpx
from cvss import CVSS3, CVSS4
from cvss.exceptions import CVSS3Error, CVSS4Error

from app.domain.inventory import Component
from app.domain.ports import SourceVuln
from app.domain.sources import MatchScope, SourceDescriptor, SourceKind

DESCRIPTOR = SourceDescriptor(
    key="osv",
    name="OSV.dev",
    homepage_url="https://osv.dev",
    description="Open Source Vulnerabilities von Google; versionsgenau pro Paket.",
    kind=SourceKind.PACKAGE_QUERY,
    scope=MatchScope.PACKAGE,
)


class HttpxOsvClient:
    descriptor = DESCRIPTOR

    def __init__(self, base_url: str, client: httpx.Client) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client

    def query(self, component: Component, api_key: str | None) -> list[SourceVuln]:  # noqa: ARG002 - Port-Signatur, OSV braucht keinen Key
        assert component.ecosystem is not None
        payload = {
            "version": component.version,
            "package": {"ecosystem": component.ecosystem.value, "name": component.name},
        }
        response = self._client.post(f"{self._base_url}/v1/query", json=payload)
        response.raise_for_status()
        data = response.json()
        return [_to_vuln(raw) for raw in data.get("vulns", [])]


def _to_vuln(raw: dict[str, Any]) -> SourceVuln:
    return SourceVuln(
        source_key="osv",
        url=f"https://osv.dev/vulnerability/{raw['id']}",
        id=raw["id"],
        aliases=list(raw.get("aliases", [])),
        summary=raw.get("summary", ""),
        details=raw.get("details", ""),
        cvss_base=_cvss_base(raw.get("severity", [])),
        fixed_version=_fixed_version(raw.get("affected", [])),
        references=[ref["url"] for ref in raw.get("references", []) if "url" in ref],
    )


def _cvss_base(severity: list[dict[str, Any]]) -> float | None:
    # Spec 5.5: CVSS v4.0 bevorzugt, sonst v3.1.
    for kind in ("CVSS_V4", "CVSS_V3"):
        for entry in severity:
            if entry.get("type") == kind:
                base = _parse_vector(kind, entry.get("score", ""))
                if base is not None:
                    return base
    return None


def _parse_vector(kind: str, vector: str) -> float | None:
    try:
        if kind == "CVSS_V4":
            return float(CVSS4(vector).base_score)
        if kind == "CVSS_V3":
            return float(CVSS3(vector).base_score)
    except (CVSS3Error, CVSS4Error):
        return None
    return None


def _fixed_version(affected: list[dict[str, Any]]) -> str | None:
    for item in affected:
        for rng in item.get("ranges", []):
            for event in rng.get("events", []):
                if "fixed" in event:
                    return str(event["fixed"])
    return None
