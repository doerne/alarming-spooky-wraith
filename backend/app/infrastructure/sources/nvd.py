"""NVD (NIST) CVE API 2.0: Stichwortsuche nach Produktname, CPE-Bereiche als Versionen.

Nur für Produkte/Runtimes ohne Paket-Ökosystem. Ein API-Key ist optional und
hebt das Rate-Limit (Header ``apiKey``).
"""

from collections.abc import Iterator, Mapping
from typing import Any

import httpx

from app.domain.inventory import Component
from app.domain.ports import AffectedPackage, RangeEvent, SourceVuln
from app.domain.sources import ApiKeyRequirement, MatchScope, SourceDescriptor, SourceKind
from app.infrastructure.sources.http_errors import get_json

_PAGE_SIZE = 2000
_MAX_PAGES = 5
_CPE_PRODUCT = 4
_CPE_VERSION = 5
_ANY_VERSION = ("*", "-", "")
_METRICS = ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30")
_BOUNDS = (
    ("versionStartIncluding", "introduced"),
    ("versionStartExcluding", "introduced"),
    ("versionEndExcluding", "fixed"),
    ("versionEndIncluding", "last_affected"),
)

DESCRIPTOR = SourceDescriptor(
    key="nvd",
    name="NVD (NIST)",
    homepage_url="https://nvd.nist.gov",
    description="Offizielle CVE-Datenbank des NIST; hier für Produkte und Runtimes "
    "(MariaDB, Redis, Java …) über CPE-Versionsbereiche.",
    kind=SourceKind.PACKAGE_QUERY,
    scope=MatchScope.PRODUCT,
    api_key_requirement=ApiKeyRequirement.OPTIONAL,
    api_key_hint="NVD-API-Key (optional, hebt das Rate-Limit)",
)


def _cpe_matches(cve: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    for configuration in cve.get("configurations") or []:
        for node in configuration.get("nodes") or []:
            for match in node.get("cpeMatch") or []:
                if match.get("vulnerable"):
                    yield match


def _affected(match: Mapping[str, Any]) -> AffectedPackage:
    parts = str(match.get("criteria", "")).split(":")
    product = parts[_CPE_PRODUCT] if len(parts) > _CPE_VERSION else ""
    version = parts[_CPE_VERSION] if len(parts) > _CPE_VERSION else ""
    if version not in _ANY_VERSION:
        return AffectedPackage(None, product, versions=(version,))
    events = tuple(
        RangeEvent(kind, str(match[field])) for field, kind in _BOUNDS if match.get(field)
    )
    if events and events[0].kind != "introduced":
        events = (RangeEvent("introduced", "0"), *events)
    return AffectedPackage(None, product, events)


def _cvss(cve: Mapping[str, Any]) -> float | None:
    metrics = cve.get("metrics") or {}
    for kind in _METRICS:
        for metric in metrics.get(kind) or []:
            score = (metric.get("cvssData") or {}).get("baseScore")
            if score is not None:
                return float(score)
    return None


def _description(cve: Mapping[str, Any]) -> str:
    descriptions = cve.get("descriptions") or []
    english = [d["value"] for d in descriptions if d.get("lang") == "en"]
    return english[0] if english else ""


def _to_vuln(cve: Mapping[str, Any]) -> SourceVuln:
    cve_id = str(cve["id"])
    return SourceVuln(
        source_key="nvd",
        id=cve_id,
        aliases=[],
        summary=_description(cve),
        details="",
        cvss_base=_cvss(cve),
        fixed_version=None,
        references=[ref["url"] for ref in cve.get("references") or [] if "url" in ref],
        url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
        affected=tuple(_affected(match) for match in _cpe_matches(cve)),
    )


class NvdSource:
    descriptor = DESCRIPTOR

    def __init__(
        self,
        client: httpx.Client,
        base_url: str = "https://services.nvd.nist.gov",
        page_size: int = _PAGE_SIZE,
    ) -> None:
        self._client = client
        self._url = f"{base_url.rstrip('/')}/rest/json/cves/2.0"
        self._page_size = page_size

    def query(self, component: Component, api_key: str | None) -> list[SourceVuln]:
        headers = {"apiKey": api_key} if api_key else {}
        vulns: list[SourceVuln] = []
        for page in range(_MAX_PAGES):
            params = {
                "keywordSearch": component.name,
                "resultsPerPage": str(self._page_size),
                "startIndex": str(page * self._page_size),
            }
            data = get_json(self._client, "GET", self._url, params=params, headers=headers)
            vulns += [_to_vuln(item["cve"]) for item in data.get("vulnerabilities") or []]
            if len(vulns) >= int(data.get("totalResults") or 0):
                break
        return vulns
