"""Abgleich der Live-Komponenten einer SBOM mit den Einträgen einer neuen Version."""

from collections.abc import Sequence
from dataclasses import dataclass, replace

from app.application.component_matching import normalize_package_name
from app.domain.inventory import Component, Ecosystem
from app.domain.sbom import SbomEntry

ComponentKey = tuple[str | None, str, str]


def _key(ecosystem: Ecosystem | None, name: str, version: str) -> ComponentKey:
    ecosystem_value = ecosystem.value if ecosystem else None
    return (ecosystem_value, normalize_package_name(ecosystem_value, name), version)


def entry_key(entry: SbomEntry) -> ComponentKey:
    return _key(entry.ecosystem, entry.name, entry.version)


def component_key(component: Component) -> ComponentKey:
    return _key(component.ecosystem, component.name, component.version)


def merge_duplicates(entries: Sequence[SbomEntry]) -> tuple[SbomEntry, ...]:
    """Fasst gleiche Einträge zusammen; direkt, sobald einer direkt ist."""
    merged: dict[ComponentKey, SbomEntry] = {}
    for entry in entries:
        key = entry_key(entry)
        existing = merged.get(key)
        if existing is None:
            merged[key] = entry
        elif entry.direct:
            merged[key] = replace(existing, direct=True)
    return tuple(merged.values())


@dataclass(frozen=True)
class Reconciliation:
    to_add: tuple[SbomEntry, ...]
    to_keep: tuple[tuple[Component, SbomEntry], ...]
    to_remove: tuple[Component, ...]


def reconcile(live: Sequence[Component], entries: Sequence[SbomEntry]) -> Reconciliation:
    """Erwartet zusammengefasste Einträge (siehe ``merge_duplicates``)."""
    live_by_key = {component_key(component): component for component in live}
    entry_by_key = {entry_key(entry): entry for entry in entries}
    return Reconciliation(
        to_add=tuple(entry for key, entry in entry_by_key.items() if key not in live_by_key),
        to_keep=tuple(
            (component, entry_by_key[key])
            for key, component in live_by_key.items()
            if key in entry_by_key
        ),
        to_remove=tuple(
            component for key, component in live_by_key.items() if key not in entry_by_key
        ),
    )
