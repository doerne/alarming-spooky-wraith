"""EUVD (ENISA): ``GET /api/search?product=…`` der European Vulnerability Database.

``aliases`` und ``references`` kommen als Text mit Zeilenumbrüchen,
Versionen als ``"<ab>, < <bis>"``.
"""

import re
from collections.abc import Mapping
from typing import Any

import httpx

from app.domain.inventory import Component
from app.domain.ports import AffectedPackage, RangeEvent, SourceVuln
from app.domain.sources import MatchScope, SourceDescriptor, SourceKind
from app.infrastructure.sources.constraints import parse_constraint
from app.infrastructure.sources.http_errors import get_json

_PAGE_SIZE = 100
_MAX_PAGES = 5
_UPPER_KIND = {"<": "fixed", "<=": "last_affected"}
# "11.4.0, < 11.4.5": nackte Untergrenze, dann Obergrenze
_START_AND_END = re.compile(r"^\s*([^\s,<>=]+)\s*,\s*(<=?)\s*(\S+)\s*$")

DESCRIPTOR = SourceDescriptor(
    key="euvd",
    name="EUVD (ENISA)",
    homepage_url="https://euvd.enisa.europa.eu",
    description="European Vulnerability Database der ENISA; hier für Produkte und Runtimes.",
    kind=SourceKind.PACKAGE_QUERY,
    scope=MatchScope.PRODUCT,
)


def euvd_version_events(text: str) -> tuple[tuple[RangeEvent, ...], tuple[str, ...]]:
    match = _START_AND_END.match(text)
    if match:
        start, operator, end = match.groups()
        return (RangeEvent("introduced", start), RangeEvent(_UPPER_KIND[operator], end)), ()
    return parse_constraint(text)


def _lines(text: str | None) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def _affected(entry: Mapping[str, Any]) -> AffectedPackage:
    name = str((entry.get("product") or {}).get("name") or "")
    events, versions = euvd_version_events(str(entry.get("product_version") or ""))
    return AffectedPackage(None, name, events, versions)


def _to_vuln(item: Mapping[str, Any]) -> SourceVuln:
    euvd_id = str(item["id"])
    score = item.get("baseScore")
    return SourceVuln(
        source_key="euvd",
        id=euvd_id,
        aliases=_lines(item.get("aliases")),
        summary=item.get("description") or "",
        details="",
        cvss_base=float(score) if score else None,
        fixed_version=None,
        references=_lines(item.get("references")),
        url=f"https://euvd.enisa.europa.eu/vulnerability/{euvd_id}",
        affected=tuple(_affected(entry) for entry in item.get("enisaIdProduct") or []),
    )


class EuvdSource:
    descriptor = DESCRIPTOR

    def __init__(
        self, client: httpx.Client, base_url: str = "https://euvdservices.enisa.europa.eu"
    ) -> None:
        self._client = client
        self._url = f"{base_url.rstrip('/')}/api/search"

    def query(self, component: Component, api_key: str | None) -> list[SourceVuln]:  # noqa: ARG002 - kein Key nötig
        vulns: list[SourceVuln] = []
        for page in range(_MAX_PAGES):
            params = {"product": component.name, "size": str(_PAGE_SIZE), "page": str(page)}
            data = get_json(self._client, "GET", self._url, params=params)
            vulns += [_to_vuln(item) for item in data.get("items") or []]
            if len(vulns) >= int(data.get("total") or 0):
                break
        return vulns
