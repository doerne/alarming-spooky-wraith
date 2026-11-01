"""Node.js-Core-Schwachstellen aus ``nodejs/security-wg`` (``vuln/core/index.json``).

Gilt für die Runtime (Komponente ohne Ökosystem, Name „Node.js“/„nodejs“/„node“).
``vulnerable`` ist ein npm-Semver-Bereich, z. B. ``<18.20.4 || >=20.0.0 <20.15.1``.
"""

import re
from collections.abc import Mapping
from typing import Any

import httpx

from app.domain.ports import AffectedPackage, RangeEvent, SourceVuln
from app.domain.sources import MatchScope, SourceDescriptor, SourceKind
from app.infrastructure.sources.constraints import parse_constraint
from app.infrastructure.sources.http_errors import get_json

_INDEX_URL = "https://raw.githubusercontent.com/nodejs/security-wg/main/vuln/core/index.json"
_NAMES = ("node.js", "nodejs", "node")
_WILDCARD = re.compile(r"^(\d+)\.x$")
_CARET = re.compile(r"^\^(\d+)\.(\d+)\.(\d+)$")

DESCRIPTOR = SourceDescriptor(
    key="nodejs",
    name="Node.js Security",
    homepage_url="https://nodejs.org/en/blog/vulnerability",
    description="Schwachstellen der Node.js-Runtime aus der Node.js Security Working Group.",
    kind=SourceKind.BULK,
    scope=MatchScope.PRODUCT,
)


def _alternative_events(alternative: str) -> tuple[RangeEvent, ...]:
    text = alternative.strip()
    if match := _WILDCARD.match(text):
        major = int(match.group(1))
        return RangeEvent("introduced", f"{major}.0.0"), RangeEvent("fixed", f"{major + 1}.0.0")
    if match := _CARET.match(text):
        major = int(match.group(1))
        return RangeEvent("introduced", text[1:]), RangeEvent("fixed", f"{major + 1}.0.0")
    return parse_constraint(text)[0]


def npm_range_events(text: str) -> tuple[RangeEvent, ...]:
    return tuple(event for part in text.split("||") for event in _alternative_events(part))


def _to_vuln(key: str, entry: Mapping[str, Any]) -> SourceVuln:
    cves = [str(cve) for cve in entry.get("cve") or []]
    events = npm_range_events(str(entry.get("vulnerable") or ""))
    ref = str(entry.get("ref") or "")
    return SourceVuln(
        source_key="nodejs",
        id=cves[0] if cves else f"NSWG-CORE-{key}",
        aliases=cves[1:],
        summary=str(entry.get("overview") or ""),
        details="",
        cvss_base=None,
        fixed_version=None,
        references=[ref] if ref else [],
        url=ref or DESCRIPTOR.homepage_url,
        affected=tuple(AffectedPackage(None, name, events) for name in _NAMES),
    )


class NodejsSource:
    descriptor = DESCRIPTOR

    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def load(self, api_key: str | None, names: frozenset[str]) -> list[SourceVuln]:  # noqa: ARG002 - kein Key nötig
        if not names:
            return []
        index = get_json(self._client, "GET", _INDEX_URL)
        return [_to_vuln(str(key), entry) for key, entry in index.items()]
