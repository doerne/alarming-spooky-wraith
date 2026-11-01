"""CVE.org (MITRE): täglicher Gesamtabzug aus dem Repo ``CVEProject/cvelistV5``.

Das Release-Asset ``*_all_CVEs_at_midnight.zip.zip`` (rund 650 MB) enthält ein
weiteres Zip mit einer JSON-Datei pro CVE. Es wird im Cache entpackt und
streamend gelesen; nur Einträge zu den gesuchten Produktnamen werden geparst.
"""

import json
import zipfile
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import httpx

from app.domain.errors import SourceAccessError
from app.domain.ports import AffectedPackage, RangeEvent, SourceVuln
from app.domain.sources import MatchScope, SourceDescriptor, SourceKind
from app.infrastructure.sources.http_cache import HttpCache
from app.infrastructure.sources.http_errors import get_json
from app.infrastructure.sources.osv_format import parse_cvss_vector

_RELEASE_URL = "https://api.github.com/repos/CVEProject/cvelistV5/releases/latest"
_ASSET_SUFFIX = "_all_CVEs_at_midnight.zip.zip"
_INNER_ARCHIVE = "cves.zip"
_REJECTED = "REJECTED"
_FROM_START = ("", "0", "*")
_METRIC_KEYS = ("cvssV4_0", "cvssV3_1", "cvssV3_0")

DESCRIPTOR = SourceDescriptor(
    key="cve-org",
    name="CVE.org (MITRE)",
    homepage_url="https://www.cve.org",
    description="Das offizielle CVE-Programm; täglicher Gesamtabzug aller CVE-Records "
    "(großer Download, wird zwischengespeichert).",
    kind=SourceKind.BULK,
    scope=MatchScope.PRODUCT,
)


def _version_entry(entry: Mapping[str, Any]) -> tuple[list[RangeEvent], list[str]]:
    version = str(entry.get("version") or "")
    upper = entry.get("lessThan") or entry.get("lessThanOrEqual")
    if not upper:
        return [], [version] if version not in _FROM_START else []
    kind = "fixed" if entry.get("lessThan") else "last_affected"
    start = "0" if version in _FROM_START else version
    return [RangeEvent("introduced", start), RangeEvent(kind, str(upper))], []


def _affected(item: Mapping[str, Any]) -> AffectedPackage:
    events: list[RangeEvent] = []
    versions: list[str] = []
    for entry in item.get("versions") or []:
        if entry.get("status") == "affected":
            entry_events, entry_versions = _version_entry(entry)
            events += entry_events
            versions += entry_versions
    return AffectedPackage(
        None, str(item.get("product") or "").lower(), tuple(events), tuple(versions)
    )


def _cvss(cna: Mapping[str, Any]) -> float | None:
    for metric in cna.get("metrics") or []:
        for key in _METRIC_KEYS:
            data = metric.get(key) or {}
            if data.get("baseScore") is not None:
                return float(data["baseScore"])
            if data.get("vectorString"):
                return parse_cvss_vector(str(data["vectorString"]))
    return None


def _to_vuln(record: Mapping[str, Any], names: frozenset[str]) -> SourceVuln | None:
    metadata = record.get("cveMetadata") or {}
    cna = (record.get("containers") or {}).get("cna") or {}
    affected = tuple(
        package
        for package in (_affected(item) for item in cna.get("affected") or [])
        if package.name in names
    )
    if metadata.get("state") == _REJECTED or not affected:
        return None
    cve_id = str(metadata["cveId"])
    descriptions = [d.get("value", "") for d in cna.get("descriptions") or []]
    return SourceVuln(
        source_key="cve-org",
        id=cve_id,
        aliases=[],
        summary=descriptions[0] if descriptions else "",
        details="",
        cvss_base=_cvss(cna),
        fixed_version=None,
        references=[ref["url"] for ref in cna.get("references") or [] if "url" in ref],
        url=f"https://www.cve.org/CVERecord?id={cve_id}",
        affected=affected,
    )


def _inner_archive(outer: Path) -> Path:
    """Entpackt das innere Zip einmal pro neuem Abzug."""
    inner = outer.with_suffix(".cves.zip")
    if inner.exists() and inner.stat().st_mtime >= outer.stat().st_mtime:
        return inner
    try:
        with zipfile.ZipFile(outer) as archive, archive.open(_INNER_ARCHIVE) as source:
            partial = inner.with_suffix(".part")
            with partial.open("wb") as target:
                while chunk := source.read(1024 * 1024):
                    target.write(chunk)
            partial.replace(inner)
    except (zipfile.BadZipFile, KeyError) as error:
        raise SourceAccessError("CVE.org-Abzug ist beschädigt oder unerwartet aufgebaut") from error
    return inner


def _records(archive_path: Path, names: frozenset[str]) -> Iterator[Mapping[str, Any]]:
    needles = [name.encode() for name in names]
    with zipfile.ZipFile(archive_path) as archive:
        for entry in archive.namelist():
            if not entry.endswith(".json"):
                continue
            raw = archive.read(entry)
            # Schneller Vorfilter: nur Dateien parsen, die einen gesuchten Namen enthalten.
            if any(needle in raw.lower() for needle in needles):
                yield json.loads(raw)


class CveOrgSource:
    descriptor = DESCRIPTOR

    def __init__(self, client: httpx.Client, cache: HttpCache) -> None:
        self._client = client
        self._cache = cache

    def load(self, api_key: str | None, names: frozenset[str]) -> list[SourceVuln]:  # noqa: ARG002 - kein Key nötig
        if not names:
            return []
        asset_name, asset_url = self._latest_asset()
        # Fester Cache-Name + Asset-Name als Version: ein Abzug pro Tag, keine Altlasten.
        outer = self._cache.fetch("cve-org", asset_url, cache_name="latest", version=asset_name)
        vulns = (_to_vuln(record, names) for record in _records(_inner_archive(outer), names))
        return [vuln for vuln in vulns if vuln is not None]

    def _latest_asset(self) -> tuple[str, str]:
        release = get_json(self._client, "GET", _RELEASE_URL)
        for asset in release.get("assets") or []:
            name = str(asset.get("name", ""))
            if name.endswith(_ASSET_SUFFIX):
                return name, str(asset["browser_download_url"])
        raise SourceAccessError("Kein CVE.org-Gesamtabzug im neuesten Release gefunden")
