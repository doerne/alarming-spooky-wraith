"""Use Case: Treffer ausgebauter SBOM-Komponenten nach einem Scan auflösen.

Läuft am Ende eines Scans ohne Quellenfehler. Gibt es für dieselbe Anwendung und
Advisory einen Treffer an einer Live-Komponente (z. B. Upgrade ohne Fix), übernimmt
dieser die Triage; sonst gilt die Lücke als behoben.
"""

from collections.abc import Callable, Iterable
from datetime import datetime

from app.application.unit_of_work import UnitOfWork
from app.domain.inventory import Component
from app.domain.vulnerability import Finding, FindingStatus

_COMMENT_SEPARATOR = "\n\n"
_KEPT_STATUSES = frozenset({FindingStatus.FALSE_POSITIVE})


def _merged_comment(first: str, second: str) -> str:
    return _COMMENT_SEPARATOR.join(comment for comment in (first, second) if comment)


class ResolveRetiredFindings:
    def __init__(self, uow: UnitOfWork, clock: Callable[[], datetime]) -> None:
        self._uow = uow
        self._clock = clock

    def execute(self) -> int:
        """Löst offene Treffer ausgebauter Komponenten auf; Anzahl behobener. Kein Commit."""
        components = {
            component.id: component
            for component in self._uow.components.list_all()
            if component.id is not None
        }
        findings = self._uow.findings.list()
        live = {
            (finding.application_id, finding.advisory_id): finding
            for finding in findings
            if not components[finding.component_id].is_retired
        }
        resolved = 0
        now = self._clock()
        for finding in findings:
            component = components[finding.component_id]
            if not component.is_retired or finding.resolved_at is not None:
                continue
            successor = live.get((finding.application_id, finding.advisory_id))
            if successor is None:
                self._mark_fixed(finding, component, now)
                resolved += 1
            else:
                self._transfer(finding, successor)
        self._remove_empty(components.values())
        return resolved

    def _mark_fixed(self, finding: Finding, component: Component, now: datetime) -> None:
        assert finding.id is not None
        status = finding.status if finding.status in _KEPT_STATUSES else FindingStatus.FIXED
        self._uow.findings.resolve(finding.id, status, now, self._resolution(component))

    def _resolution(self, component: Component) -> str:
        assert component.retired_in_version_id is not None
        version = self._uow.sbom_versions.get(component.retired_in_version_id)
        sbom = self._uow.sboms.get(version.sbom_id)
        return f"Komponente ausgebaut mit SBOM {sbom.name} {version.label}"

    def _transfer(self, finding: Finding, successor: Finding) -> None:
        assert finding.id is not None
        assert successor.id is not None
        status = finding.status if successor.status == FindingStatus.OPEN else successor.status
        comment = _merged_comment(successor.comment, finding.comment)
        self._uow.findings.save_triage(successor.id, status, comment)
        self._uow.findings.delete(finding.id)
        # Für weitere Vorgänger derselben Lücke gilt die übernommene Triage.
        successor.status = status
        successor.comment = comment

    def _remove_empty(self, components: Iterable[Component]) -> None:
        in_use = {finding.component_id for finding in self._uow.findings.list()}
        empty = [
            component.id
            for component in components
            if component.is_retired and component.id is not None and component.id not in in_use
        ]
        self._uow.components.delete_many(empty)
