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

    application_id: int | None = None  # Scope (Inventar); bestimmt unfiltered_total
    application_ids: frozenset[int] = frozenset()  # Filter (Dashboard), mehrfach
    severities: frozenset[Severity] = frozenset()
    statuses: frozenset[FindingStatus] = frozenset()
    ecosystems: frozenset[str] = frozenset()
    query: str = ""  # Freitext: Advisory-ID, CVE-ID, Titel oder Komponente
    advisory_ids: frozenset[str] = frozenset()
    component_names: frozenset[str] = frozenset()


@dataclass(frozen=True)
class FindingList:
    items: list[FindingView]
    unfiltered_total: int  # im Anwendungs-Scope, vor den übrigen Filtern


Predicate = Callable[[FindingView], bool]


def _contains(needle: str, texts: Callable[[FindingView], tuple[str, ...]]) -> Predicate:
    def matches(view: FindingView) -> bool:
        return any(needle in text.lower() for text in texts(view))

    return matches


def _advisory_texts(view: FindingView) -> tuple[str, ...]:
    return (view.advisory_id, view.cve_id or "", view.title)


def _all_texts(view: FindingView) -> tuple[str, ...]:
    return (*_advisory_texts(view), view.component_name)


def _predicates(criteria: FindingFilter) -> list[Predicate]:
    query = criteria.query.strip().lower()
    # (aktiv?, Prüfung) - inaktive Filter fallen weg.
    checks: list[tuple[bool, Predicate]] = [
        (
            bool(criteria.application_ids),
            lambda view: view.application_id in criteria.application_ids,
        ),
        (bool(criteria.severities), lambda view: view.risk_level in criteria.severities),
        (bool(criteria.statuses), lambda view: view.status in criteria.statuses),
        (
            bool(criteria.ecosystems),
            lambda view: (view.ecosystem or NO_ECOSYSTEM) in criteria.ecosystems,
        ),
        (bool(criteria.advisory_ids), lambda view: view.advisory_id in criteria.advisory_ids),
        (
            bool(criteria.component_names),
            lambda view: view.component_name in criteria.component_names,
        ),
        (bool(query), _contains(query, _all_texts)),
    ]
    return [check for active, check in checks if active]


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
