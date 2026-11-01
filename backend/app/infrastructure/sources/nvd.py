"""NVD (NIST) CVE API 2.0: Stichwortsuche nach Produktname, CPE-Bereiche als Versionen.

Nur für Produkte/Runtimes ohne Paket-Ökosystem. Ein API-Key ist optional und
hebt das Rate-Limit (Header ``apiKey``).
"""

import logging
import time
from collections.abc import Callable, Iterator, Mapping
from typing import Any

import httpx

from app.domain.inventory import Component
from app.domain.ports import AffectedPackage, RangeEvent, SourceVuln
from app.domain.sources import ApiKeyRequirement, MatchScope, SourceDescriptor, SourceKind
from app.infrastructure.sources.http_errors import get_json

_logger = logging.getLogger(__name__)
_PAGE_SIZE = 500
_MAX_PAGES = 20
# NVD erlaubt ohne Key 5, mit Key 50 Anfragen pro 30 Sekunden.
_INTERVAL_WITHOUT_KEY = 6.0
_INTERVAL_WITH_KEY = 0.6
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


class _Throttle:
    """Hält den Mindestabstand zwischen zwei Anfragen ein."""

    def __init__(self, sleep: Callable[[float], None], monotonic: Callable[[], float]) -> None:
        self._sleep = sleep
        self._monotonic = monotonic
        self._last: float | None = None

    def wait(self, interval: float) -> None:
        if self._last is not None:
            remaining = interval - (self._monotonic() - self._last)
            if remaining > 0:
                self._sleep(remaining)
        self._last = self._monotonic()


def _concerns(vuln: SourceVuln, product: str) -> bool:
    return any(package.name == product for package in vuln.affected)


class NvdSource:
    descriptor = DESCRIPTOR

    def __init__(
        self,
        client: httpx.Client,
        *,
        page_size: int = _PAGE_SIZE,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client
        self._url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        self._page_size = page_size
        self._throttle = _Throttle(sleep, monotonic)

    def query(self, component: Component, api_key: str | None) -> list[SourceVuln]:
        headers = {"apiKey": api_key} if api_key else {}
        interval = _INTERVAL_WITH_KEY if api_key else _INTERVAL_WITHOUT_KEY
        product = component.name.lower()
        vulns: list[SourceVuln] = []
        for page in range(_MAX_PAGES):
            self._throttle.wait(interval)
            data = get_json(
                self._client,
                "GET",
                self._url,
                params=self._params(component, page),
                headers=headers,
            )
            # Stichwortsuche trifft auch Fremdprodukte: pro Seite gleich aussortieren (Speicher).
            page_vulns = (_to_vuln(item["cve"]) for item in data.get("vulnerabilities") or [])
            vulns += [vuln for vuln in page_vulns if _concerns(vuln, product)]
            if (page + 1) * self._page_size >= int(data.get("totalResults") or 0):
                return vulns
        _logger.warning(
            "NVD: Treffer für %s nach %d Seiten abgeschnitten", component.name, _MAX_PAGES
        )
        return vulns

    def _params(self, component: Component, page: int) -> dict[str, str]:
        return {
            "keywordSearch": component.name,
            "resultsPerPage": str(self._page_size),
            "startIndex": str(page * self._page_size),
        }
