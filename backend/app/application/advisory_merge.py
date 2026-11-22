"""Führt dieselbe Schwachstelle aus mehreren Quellen zu einer Advisory zusammen.

Abweichende Werte entscheidet eine feste Rangfolge (Spec §7), damit der
Risk Score nicht von Lauf zu Lauf schwankt.
"""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass

from app.domain.ports import SourceReference, SourceVuln
from app.domain.vulnerability import is_valid_advisory_id

_CVE_PREFIX = "CVE-"
_GHSA_PREFIX = "GHSA-"


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
    aliases: tuple[str, ...] = ()


def identity_ids(vuln: SourceVuln) -> frozenset[str]:
    """Alle zulässigen IDs, unter denen eine Quelle die Schwachstelle führt.

    Fremd-IDs werden geprüft, damit kein unzulässiger Alias kanonisch wird oder beim
    Speichern den ganzen Lauf abbricht. Ohne zulässige ID bleibt die eigene ID stehen
    (der Store verwirft sie dann wie bisher).
    """
    candidates = (vuln.id, *vuln.aliases)
    valid = frozenset(identifier for identifier in candidates if is_valid_advisory_id(identifier))
    return valid or frozenset([vuln.id])


def canonical_key(ids: Iterable[str]) -> tuple[str, str | None]:
    """(advisory_id, cve_id): kleinste CVE-ID, sonst kleinste GHSA-ID, sonst kleinste ID."""
    unique = sorted(set(ids))
    for prefix in (_CVE_PREFIX, _GHSA_PREFIX):
        matching = [identifier for identifier in unique if identifier.startswith(prefix)]
        if matching:
            chosen = matching[0]
            return chosen, chosen if prefix == _CVE_PREFIX else None
    return unique[0], None


def group_by_identity[T](
    items: Sequence[T], ids_of: Callable[[T], frozenset[str]]
) -> list[list[T]]:
    """Fasst Einträge zusammen, die (auch über Ecken) eine ID teilen. Reihenfolge stabil."""
    parent = list(range(len(items)))

    def root(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    owner: dict[str, int] = {}
    for index, item in enumerate(items):
        for identifier in ids_of(item):
            if identifier in owner:
                parent[root(index)] = root(owner[identifier])
            else:
                owner[identifier] = index
    groups: dict[int, list[T]] = {}
    for index, item in enumerate(items):
        groups.setdefault(root(index), []).append(item)
    return list(groups.values())


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
    all_ids = frozenset(identifier for vuln in vulns for identifier in identity_ids(vuln))
    advisory_id, cve_id = canonical_key(all_ids)
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
        aliases=tuple(sorted(all_ids - {advisory_id})),
    )
