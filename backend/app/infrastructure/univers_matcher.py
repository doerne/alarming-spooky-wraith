"""VersionMatcher-Adapter auf Basis von ``univers``.

Wertet OSV-Bereiche (introduced/fixed/last_affected/limit) und explizite
Versionslisten aus. Was sich nicht parsen lässt, gilt als nicht betroffen.
"""

import re

from univers.versions import (
    ComposerVersion,
    DebianVersion,
    GolangVersion,
    InvalidVersion,
    MavenVersion,
    NugetVersion,
    PypiVersion,
    RubygemsVersion,
    SemverVersion,
    Version,
)

from app.domain.ports import AffectedPackage, RangeEvent

# GenericVersion/IntdotVersion sortieren 1.9 > 1.10 - DebianVersion vergleicht
# numerisch und deckt Hackage, CRAN, opam und Produkte ohne Ökosystem ab.
_FALLBACK: type[Version] = DebianVersion
_VERSION_CLASS: dict[str, type[Version]] = {
    "npm": SemverVersion,
    "crates.io": SemverVersion,
    "PyPI": PypiVersion,
    "Maven": MavenVersion,
    "RubyGems": RubygemsVersion,
    "Go": GolangVersion,
    "NuGet": NugetVersion,
    "Packagist": ComposerVersion,
}
_INTRODUCED_FROM_START = "0"
# "1.x" oder "2.*" sind Bereiche, keine Versionen.
_WILDCARD_SEGMENT = re.compile(r"(^|[.])[xX*]([.]|$)")


def _parse(version_class: type[Version], value: str) -> Version | None:
    if _WILDCARD_SEGMENT.search(value):
        return None
    try:
        return version_class(value)
    except (InvalidVersion, ValueError, TypeError):
        return None


def _parsed_events(
    version_class: type[Version], events: tuple[RangeEvent, ...]
) -> list[tuple[Version | None, str]] | None:
    """Events nach Version sortiert; ``introduced: 0`` steht als None ganz vorn.

    Ist eine Grenze unlesbar, ist der ganze Bereich unbrauchbar → None.
    """
    starts: list[tuple[Version | None, str]] = []
    bounded: list[tuple[Version, str]] = []
    for event in events:
        if event.kind == "introduced" and event.version == _INTRODUCED_FROM_START:
            starts.append((None, event.kind))
            continue
        version = _parse(version_class, event.version)
        if version is None:
            return None
        bounded.append((version, event.kind))
    bounded.sort(key=lambda item: item[0])
    return [*starts, *bounded]


def _apply_event(affected: bool, current: Version, bound: Version | None, kind: str) -> bool:
    if kind == "introduced":
        return True if bound is None or current >= bound else affected
    if bound is None:
        return affected
    if kind in ("fixed", "limit") and current >= bound:
        return False
    if kind == "last_affected" and current > bound:
        return False
    return affected


class UniversVersionMatcher:
    def is_affected(self, ecosystem: str | None, version: str, package: AffectedPackage) -> bool:
        version_class = _VERSION_CLASS.get(ecosystem or "", _FALLBACK)
        current = _parse(version_class, version)
        if current is None:
            return False
        if any(_parse(version_class, listed) == current for listed in package.versions):
            return True
        events = _parsed_events(version_class, package.events)
        if events is None:
            return False
        affected = False
        for bound, kind in events:
            affected = _apply_event(affected, current, bound, kind)
        return affected
