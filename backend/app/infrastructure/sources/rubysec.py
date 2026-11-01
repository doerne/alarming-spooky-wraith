"""Ruby Advisory DB (rubysec): Repo-Zip mit einer YAML-Datei pro Advisory.

RubySec nennt sichere Versionen (``patched_versions``, ``unaffected_versions``);
daraus werden OSV-Ereignisse für die betroffenen Bereiche abgeleitet.
"""

import re
from collections.abc import Mapping, Sequence
from typing import Any

import yaml

from app.domain.ports import AffectedPackage, RangeEvent, SourceVuln
from app.domain.sources import MatchScope, SourceDescriptor, SourceKind
from app.infrastructure.sources.archives import open_archive
from app.infrastructure.sources.http_cache import HttpCache

_ARCHIVE_URL = "https://github.com/rubysec/ruby-advisory-db/archive/refs/heads/master.zip"
_GEM_FOLDER = "/gems/"
_RUBYGEMS = "RubyGems"
_TOKEN = re.compile(r"(~>|>=|>|<=|<|=)\s*([^\s,]+)")

DESCRIPTOR = SourceDescriptor(
    key="rubysec",
    name="Ruby Advisory DB",
    homepage_url="https://rubysec.com",
    description="Community-Datenbank für Schwachstellen in Ruby-Gems.",
    kind=SourceKind.BULK,
    scope=MatchScope.PACKAGE,
    ecosystems=frozenset({_RUBYGEMS}),
)


def _pessimistic_upper(version: str) -> str:
    """``~> 6.1.7`` erlaubt bis ausschließlich 6.2."""
    parts = version.split(".")
    if len(parts) > 1:
        parts = parts[:-1]
    head = parts[-1]
    parts[-1] = str(int(head) + 1) if head.isdigit() else head
    return ".".join(parts)


def _safe_range(constraint: str) -> tuple[str | None, str | None]:
    """Eine Patched-Bedingung → (sicher ab, wieder unsicher ab)."""
    lower: str | None = None
    upper: str | None = None
    for operator, version in _TOKEN.findall(constraint):
        if operator == "~>":
            lower = lower or version
            upper = _pessimistic_upper(version)
        elif operator in (">=", ">"):
            lower = version
    return lower, upper


def _unaffected_start(unaffected: Sequence[str]) -> str:
    for constraint in unaffected:
        for operator, version in _TOKEN.findall(constraint):
            if operator in ("<", "<="):
                return str(version)
    return "0"


def rubysec_events(patched: Sequence[str], unaffected: Sequence[str]) -> tuple[RangeEvent, ...]:
    events = [RangeEvent("introduced", _unaffected_start(unaffected))]
    for constraint in patched:
        lower, upper = _safe_range(constraint)
        if lower:
            events.append(RangeEvent("fixed", lower))
        if upper:
            events.append(RangeEvent("introduced", upper))
    return tuple(events)


def _identity(data: Mapping[str, Any]) -> tuple[str, list[str]]:
    cve = f"CVE-{data['cve']}" if data.get("cve") else None
    ghsa = f"GHSA-{data['ghsa']}" if data.get("ghsa") else None
    ids = [identifier for identifier in (cve, ghsa) if identifier]
    if not ids:
        ids = [f"OSVDB-{data.get('osvdb')}"]
    return ids[0], ids[1:]


def _cvss(data: Mapping[str, Any]) -> float | None:
    for key in ("cvss_v4", "cvss_v3", "cvss_v2"):
        if data.get(key):
            return float(data[key])
    return None


def _to_vuln(data: Mapping[str, Any]) -> SourceVuln:
    vuln_id, aliases = _identity(data)
    events = rubysec_events(
        data.get("patched_versions") or [], data.get("unaffected_versions") or []
    )
    url = str(data.get("url") or "")
    return SourceVuln(
        source_key="rubysec",
        id=vuln_id,
        aliases=aliases,
        summary=str(data.get("title") or ""),
        details=str(data.get("description") or ""),
        cvss_base=_cvss(data),
        fixed_version=None,
        references=[url] if url else [],
        url=url or "https://rubysec.com",
        affected=(AffectedPackage(_RUBYGEMS, str(data.get("gem", "")), events),),
    )


def _gem_of(entry: str) -> str | None:
    if _GEM_FOLDER not in entry or not entry.endswith(".yml"):
        return None
    return entry.split(_GEM_FOLDER, 1)[1].split("/", 1)[0].lower()


class RubysecSource:
    descriptor = DESCRIPTOR

    def __init__(self, cache: HttpCache) -> None:
        self._cache = cache

    def load(self, api_key: str | None, names: frozenset[str]) -> list[SourceVuln]:  # noqa: ARG002 - kein Key nötig
        if not names:
            return []
        path = self._cache.fetch("rubysec", _ARCHIVE_URL)
        vulns: list[SourceVuln] = []
        with open_archive(path, DESCRIPTOR.name) as archive:
            for entry in archive.namelist():
                if _gem_of(entry) in names:
                    vulns.append(_to_vuln(yaml.safe_load(archive.read(entry))))
        return vulns
