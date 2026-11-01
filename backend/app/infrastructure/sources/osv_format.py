"""Parser für das OSV-Schema (JSON/YAML). Nutzen mehrere Quellen.

Der CVSS-Basisscore wird aus dem Vektor der ``severity``-Einträge berechnet
(v4.0 bevorzugt, sonst v3.x).
"""

from collections.abc import Mapping, Sequence
from typing import Any

from cvss import CVSS3, CVSS4
from cvss.exceptions import CVSS3Error, CVSS4Error

from app.domain.ports import AffectedPackage, RangeEvent, SourceVuln

_EVENT_KINDS = ("introduced", "fixed", "last_affected", "limit")
_GIT_RANGE = "GIT"  # Commit-Hashes, nicht mit Versionen vergleichbar
_OSV_URL = "https://osv.dev/vulnerability/{id}"


def parse_osv_record(raw: Mapping[str, Any], source_key: str, url: str | None = None) -> SourceVuln:
    references = [ref["url"] for ref in raw.get("references") or [] if "url" in ref]
    affected = tuple(_affected(item) for item in raw.get("affected") or [])
    return SourceVuln(
        source_key=source_key,
        id=str(raw["id"]),
        aliases=[str(alias) for alias in raw.get("aliases") or []],
        summary=str(raw.get("summary") or ""),
        details=str(raw.get("details") or ""),
        cvss_base=cvss_base(raw.get("severity") or []),
        fixed_version=_fixed_version(affected),
        references=references,
        url=url or _default_url(source_key, str(raw["id"]), references),
        affected=affected,
    )


def _default_url(source_key: str, vuln_id: str, references: Sequence[str]) -> str:
    if source_key == "osv" or not references:
        return _OSV_URL.format(id=vuln_id)
    return references[0]


def _affected(item: Mapping[str, Any]) -> AffectedPackage:
    package = item.get("package") or {}
    events = tuple(
        RangeEvent(kind, str(event[kind]))
        for range_ in item.get("ranges") or []
        if range_.get("type") != _GIT_RANGE
        for event in range_.get("events") or []
        for kind in _EVENT_KINDS
        if kind in event
    )
    return AffectedPackage(
        ecosystem=package.get("ecosystem"),
        name=str(package.get("name") or ""),
        events=events,
        versions=tuple(str(version) for version in item.get("versions") or []),
    )


def _fixed_version(affected: Sequence[AffectedPackage]) -> str | None:
    for package in affected:
        for event in package.events:
            if event.kind == "fixed":
                return event.version
    return None


def cvss_base(severity: Sequence[Mapping[str, Any]]) -> float | None:
    for kind in ("CVSS_V4", "CVSS_V3"):
        for entry in severity:
            if entry.get("type") == kind:
                base = parse_cvss_vector(str(entry.get("score", "")))
                if base is not None:
                    return base
    return None


def parse_cvss_vector(vector: str) -> float | None:
    """Basisscore aus einem CVSS-v3/v4-Vektor; None, wenn unlesbar."""
    try:
        if vector.startswith("CVSS:4"):
            return float(CVSS4(vector).base_score)
        if vector.startswith("CVSS:3"):
            return float(CVSS3(vector).base_score)
    except (CVSS3Error, CVSS4Error):
        return None
    return None
