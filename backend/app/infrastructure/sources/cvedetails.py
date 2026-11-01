"""CVEdetails.com: ``GET /api/v1/vulnerability/search`` mit Bearer-Token.

Die API filtert nach Produkt und Version selbst; Treffer gelten daher für
genau die abgefragte Version. Hinweis: Die Parameternamen ließen sich ohne
Konto nicht gegen die Doku prüfen (Doku-Seite 403) - mit dem ersten Token
verifizieren. Nutzungsbedingungen vor dem Aktivieren prüfen.
"""

from collections.abc import Mapping
from typing import Any

import httpx

from app.domain.inventory import Component
from app.domain.ports import AffectedPackage, SourceVuln
from app.domain.sources import ApiKeyRequirement, MatchScope, SourceDescriptor, SourceKind
from app.infrastructure.sources.http_errors import get_json
from app.infrastructure.sources.names import require_key

_PAGE_SIZE = 100

DESCRIPTOR = SourceDescriptor(
    key="cvedetails",
    name="CVEdetails.com",
    homepage_url="https://www.cvedetails.com",
    description="Übersichtliche CVE-Statistiken pro Produkt und Hersteller. "
    "Nutzungsbedingungen von CVEdetails prüfen, bevor die Quelle aktiviert wird.",
    kind=SourceKind.PACKAGE_QUERY,
    scope=MatchScope.PRODUCT,
    api_key_requirement=ApiKeyRequirement.REQUIRED,
    api_key_hint="API-Token von cvedetails.com",
)


def _to_vuln(item: Mapping[str, Any], component: Component) -> SourceVuln:
    cve_id = str(item["cveId"])
    score = item.get("maxCvssBaseScore")
    return SourceVuln(
        source_key="cvedetails",
        id=cve_id,
        aliases=[],
        summary=item.get("summary") or "",
        details="",
        cvss_base=float(score) if score else None,
        fixed_version=None,
        references=[],
        url=f"https://www.cvedetails.com/cve/{cve_id}/",
        affected=(AffectedPackage(None, component.name.lower(), versions=(component.version,)),),
    )


class CvedetailsSource:
    descriptor = DESCRIPTOR

    def __init__(self, client: httpx.Client, base_url: str = "https://www.cvedetails.com") -> None:
        self._client = client
        self._url = f"{base_url.rstrip('/')}/api/v1/vulnerability/search"

    def query(self, component: Component, api_key: str | None) -> list[SourceVuln]:
        token = require_key(api_key)
        params = {
            "productName": component.name,
            "versionString": component.version,
            "resultsPerPage": str(_PAGE_SIZE),
        }
        data = get_json(
            self._client,
            "GET",
            self._url,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        return [_to_vuln(item, component) for item in data.get("results") or []]
