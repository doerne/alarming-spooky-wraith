"""Use Case: Treffer ausgebauter SBOM-Komponenten nach einem Scan auflösen.

Läuft am Ende jedes Scans. Gibt es für dieselbe Anwendung und Advisory einen Treffer an
einer Live-Komponente (z. B. Upgrade ohne Fix), übernimmt dieser die Triage; sonst gilt
die Lücke als behoben - außer eine Quelle, die sie bisher gemeldet hat, ist in diesem Lauf
ausgefallen (dann wird bis zum nächsten Lauf gewartet).
"""

from collections.abc import Callable, Iterable
from datetime import datetime

from app.application.unit_of_work import UnitOfWork
from app.domain.inventory import Component
from app.domain.ports import AdvisoryStore
from app.domain.vulnerability import (
    Finding,
    FindingResolution,
    FindingStatus,
    ResolutionSource,
)

_COMMENT_SEPARATOR = "\n\n"
_KEPT_STATUSES = frozenset({FindingStatus.FALSE_POSITIVE})


def _merged_comment(first: str, second: str) -> str:
    return _COMMENT_SEPARATOR.join(comment for comment in (first, second) if comment)


class ResolveRetiredFindings:
    def __init__(
        self, uow: UnitOfWork, store: AdvisoryStore, clock: Callable[[], datetime]
    ) -> None:
        self._uow = uow
        self._store = store
        self._clock = clock

    def execute(
        self, failed_sources: frozenset[str] = frozenset(), eligible: frozenset[int] | None = None
    ) -> int:
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
            if not self._is_pending(component, finding, eligible):
                continue
            successor = live.get((finding.application_id, finding.advisory_id))
            if successor is not None:
                self._transfer(finding, successor)
            elif not self._reporter_failed(finding.advisory_id, failed_sources):
                self._mark_fixed(finding, component, now)
                resolved += 1
        self._remove_empty(components.values())
        return resolved

    @staticmethod
    def _is_pending(
        component: Component, finding: Finding, eligible: frozenset[int] | None
    ) -> bool:
        """Noch offen und (falls angegeben) schon vor dem Lauf ausgebaut."""
        in_scope = eligible is None or component.id in eligible
        return component.is_retired and finding.resolved_at is None and in_scope

    def _reporter_failed(self, advisory_id: str, failed_sources: frozenset[str]) -> bool:
        """Ob eine Quelle ausfiel, die diese Lücke melden könnte (unbekannte Herkunft: jede)."""
        if not failed_sources:
            return False
        document = self._store.read_document(advisory_id)
        if document is None or not document.sources:
            return True
        return any(source.source_key in failed_sources for source in document.sources)

    def _mark_fixed(self, finding: Finding, component: Component, now: datetime) -> None:
        assert finding.id is not None
        status = finding.status if finding.status in _KEPT_STATUSES else FindingStatus.FIXED
        self._uow.findings.resolve(
            finding.id,
            FindingResolution(status, now, self._resolution(component), ResolutionSource.SBOM),
        )

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
