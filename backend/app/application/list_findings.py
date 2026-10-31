"""Use Case: Funde fuer die Uebersicht auflisten (nach Risk Score sortiert)."""

from dataclasses import dataclass

from app.application.unit_of_work import UnitOfWork
from app.domain.inventory import Component
from app.domain.vulnerability import Finding, FindingStatus, Severity


@dataclass(frozen=True)
class FindingView:
    advisory_id: str
    cve_id: str | None
    title: str
    application_name: str
    component_name: str
    component_version: str
    ecosystem: str | None
    risk_score: int
    risk_level: Severity
    fix_version: str | None
    status: FindingStatus


class ListFindings:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, application_id: int | None = None) -> list[FindingView]:
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
            title=advisory.title,
            application_name=application.name,
            component_name=component.name,
            component_version=component.version,
            ecosystem=component.ecosystem.value if component.ecosystem else None,
            risk_score=finding.risk.value,
            risk_level=finding.risk.level,
            fix_version=advisory.fixed_version,
            status=finding.status,
        )
