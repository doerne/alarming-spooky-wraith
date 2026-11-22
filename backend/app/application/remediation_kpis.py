"""Use Case: Fristen und Update-Ziele des offenen Bestands, optional für eine Anwendung."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.application.unit_of_work import UnitOfWork
from app.domain.inventory import Component
from app.domain.ports import VersionComparator
from app.domain.remediation import (
    DeadlineSummary,
    OpenItem,
    UpdateSummary,
    compute_deadlines,
    compute_update_targets,
)
from app.domain.vulnerability import Finding, is_closed


@dataclass(frozen=True)
class RemediationKpis:
    deadlines: DeadlineSummary
    updates: UpdateSummary


class GetRemediationKpis:
    def __init__(
        self,
        uow: UnitOfWork,
        clock: Callable[[], datetime],
        versions: VersionComparator,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._versions = versions

    def execute(self, application_id: int | None = None) -> RemediationKpis:
        findings = self._uow.findings.list()
        if application_id is not None:
            self._uow.applications.get(application_id)  # EntityNotFoundError
            findings = [f for f in findings if f.application_id == application_id]
        open_findings = [f for f in findings if not is_closed(f.status)]
        items = self._open_items(open_findings)
        return RemediationKpis(
            deadlines=compute_deadlines(open_findings, self._clock()),
            updates=compute_update_targets(items, self._versions),
        )

    def _open_items(self, findings: list[Finding]) -> list[OpenItem]:
        components: dict[int, Component] = {
            component.id: component
            for component in self._uow.components.list_all()
            if component.id is not None
        }
        return [self._to_item(finding, components[finding.component_id]) for finding in findings]

    def _to_item(self, finding: Finding, component: Component) -> OpenItem:
        return OpenItem(
            package_name=component.name,
            ecosystem=component.ecosystem.value if component.ecosystem else None,
            found_version=finding.found_version,
            fixed_version=self._uow.advisories.get(finding.advisory_id).fixed_version,
            application_name=self._uow.applications.get(finding.application_id).name,
        )
