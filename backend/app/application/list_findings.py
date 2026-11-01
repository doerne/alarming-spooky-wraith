"""Use Case: Funde fuer die Uebersicht auflisten (nach Risk Score sortiert, filterbar)."""

from collections.abc import Callable
from dataclasses import dataclass

from app.application.unit_of_work import UnitOfWork
from app.domain.inventory import Component
from app.domain.vulnerability import Finding, FindingStatus, Severity


@dataclass(frozen=True)
class FindingView:
    advisory_id: str
    cve_id: str | None
    title: str
    application_id: int
    application_name: str
    component_id: int
    component_name: str
    component_version: str
    ecosystem: str | None
    risk_score: int
    risk_level: Severity
    fix_version: str | None
    status: FindingStatus


# Sonderwert im Ökosystem-Filter: Komponenten ohne Paket-Ökosystem (Produkte/Runtimes).
NO_ECOSYSTEM = "none"


@dataclass(frozen=True)
class FindingFilter:
    """Werte eines Filters sind ODER-verknüpft, verschiedene Filter UND."""

    application_id: int | None = None
    severities: frozenset[Severity] = frozenset()
    statuses: frozenset[FindingStatus] = frozenset()
    ecosystems: frozenset[str] = frozenset()
    query: str = ""


@dataclass(frozen=True)
class FindingList:
    items: list[FindingView]
    unfiltered_total: int  # im Anwendungs-Scope, vor den übrigen Filtern


def _query_matches(needle: str) -> Callable[[FindingView], bool]:
    def matches(view: FindingView) -> bool:
        haystack = (view.advisory_id, view.cve_id or "", view.title, view.component_name)
        return any(needle in text.lower() for text in haystack)

    return matches


def _predicates(finding_filter: FindingFilter) -> list[Callable[[FindingView], bool]]:
    predicates: list[Callable[[FindingView], bool]] = []
    if finding_filter.severities:
        predicates.append(lambda view: view.risk_level in finding_filter.severities)
    if finding_filter.statuses:
        predicates.append(lambda view: view.status in finding_filter.statuses)
    if finding_filter.ecosystems:
        predicates.append(
            lambda view: (view.ecosystem or NO_ECOSYSTEM) in finding_filter.ecosystems
        )
    needle = finding_filter.query.strip().lower()
    if needle:
        predicates.append(_query_matches(needle))
    return predicates


class ListFindings:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, finding_filter: FindingFilter | None = None) -> FindingList:
        finding_filter = finding_filter or FindingFilter()
        scoped = self._scoped_views(finding_filter.application_id)
        predicates = _predicates(finding_filter)
        items = [view for view in scoped if all(check(view) for check in predicates)]
        return FindingList(items=items, unfiltered_total=len(scoped))

    def _scoped_views(self, application_id: int | None) -> list[FindingView]:
        components: dict[int, Component] = {
            component.id: component
            for component in self._uow.components.list_all()
            if component.id is not None
        }
        findings = [
            finding
            for finding in self._uow.findings.list()
            if application_id is None or finding.application_id == application_id
        ]
        views = [self._to_view(finding, components) for finding in findings]
        return sorted(views, key=lambda view: view.risk_score, reverse=True)

    def _to_view(self, finding: Finding, components: dict[int, Component]) -> FindingView:
        advisory = self._uow.advisories.get(finding.advisory_id)
        component = components[finding.component_id]
        application = self._uow.applications.get(finding.application_id)
        return FindingView(
            advisory_id=finding.advisory_id,
            cve_id=advisory.cve_id,
            application_id=finding.application_id,
            title=advisory.title,
            application_name=application.name,
            component_id=finding.component_id,
            component_name=component.name,
            component_version=component.version,
            ecosystem=component.ecosystem.value if component.ecosystem else None,
            risk_score=finding.risk.value,
            risk_level=finding.risk.level,
            fix_version=advisory.fixed_version,
            status=finding.status,
        )
