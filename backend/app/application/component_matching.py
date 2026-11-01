"""Gleicht Komponenten mit den betroffenen Paketen einer Schwachstelle ab."""

import re

from app.domain.inventory import Component
from app.domain.ports import AffectedPackage, SourceVuln, VersionMatcher
from app.domain.sources import MatchScope

_PYPI_SEPARATORS = re.compile(r"[-_.]+")


def normalize_package_name(ecosystem: str | None, name: str) -> str:
    lowered = name.strip().lower()
    if ecosystem == "PyPI":
        return _PYPI_SEPARATORS.sub("-", lowered)
    return lowered


class ComponentMatcher:
    def __init__(self, versions: VersionMatcher) -> None:
        self._versions = versions

    def matches(self, component: Component, vuln: SourceVuln, scope: MatchScope) -> bool:
        return any(self._matches_package(component, package, scope) for package in vuln.affected)

    def _matches_package(
        self, component: Component, package: AffectedPackage, scope: MatchScope
    ) -> bool:
        ecosystem = component.ecosystem.value if component.ecosystem else None
        if not _same_name(ecosystem, component.name, package.name):
            return False
        if scope == MatchScope.NAME:
            return True
        if package.ecosystem is not None and package.ecosystem != ecosystem:
            return False
        if not package.events and not package.versions:
            return False
        return self._versions.is_affected(ecosystem, component.version, package)


def _same_name(ecosystem: str | None, left: str, right: str) -> bool:
    return normalize_package_name(ecosystem, left) == normalize_package_name(ecosystem, right)
