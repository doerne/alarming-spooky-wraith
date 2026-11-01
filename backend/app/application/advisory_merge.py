"""Führt dieselbe Schwachstelle aus mehreren Quellen zu einer Advisory zusammen.

Abweichende Werte entscheidet eine feste Rangfolge (Spec §7), damit der
Risk Score nicht von Lauf zu Lauf schwankt.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from app.domain.ports import SourceReference, SourceVuln

_CVE_PREFIX = "CVE-"


@dataclass(frozen=True)
class MergedAdvisory:
    advisory_id: str
    cve_id: str | None
    title: str
    description: str
    details: str
    cvss_base: float | None
    fixed_version: str | None
    references: list[str]
    sources: list[SourceReference]


def advisory_key(vuln: SourceVuln) -> tuple[str, str | None]:
    """(advisory_id, cve_id): CVE-ID bevorzugt, sonst die eigene ID der Quelle."""
    if vuln.id.startswith(_CVE_PREFIX):
        return vuln.id, vuln.id
    for alias in vuln.aliases:
        if alias.startswith(_CVE_PREFIX):
            return alias, alias
    return vuln.id, None


def _ranked(vulns: Sequence[SourceVuln], order: Sequence[str]) -> list[SourceVuln]:
    def rank(vuln: SourceVuln) -> int:
        return order.index(vuln.source_key) if vuln.source_key in order else len(order)

    return sorted(vulns, key=rank)


def _first[T](ranked: Sequence[SourceVuln], pick: Callable[[SourceVuln], T | None]) -> T | None:
    for vuln in ranked:
        value = pick(vuln)
        if value is not None and value != "":
            return value
    return None


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def merge_vulns(vulns: Sequence[SourceVuln], order: Sequence[str]) -> MergedAdvisory:
    ranked = _ranked(vulns, order)
    advisory_id, cve_id = advisory_key(ranked[0])
    summary = _first(ranked, lambda vuln: vuln.summary) or ""
    return MergedAdvisory(
        advisory_id=advisory_id,
        cve_id=cve_id,
        title=summary or advisory_id,
        description=summary,
        details=_first(ranked, lambda vuln: vuln.details) or summary,
        cvss_base=_first(ranked, lambda vuln: vuln.cvss_base),
        fixed_version=_first(ranked, lambda vuln: vuln.fixed_version),
        references=_unique([url for vuln in ranked for url in vuln.references]),
        sources=list(dict.fromkeys(SourceReference(vuln.source_key, vuln.url) for vuln in ranked)),
    )
