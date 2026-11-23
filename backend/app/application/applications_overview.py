"""Use Case: Kennzahlen aller Anwendungen für die Inventar-Übersicht in einem Durchgang."""

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.application.unit_of_work import UnitOfWork
from app.domain.application_overview import (
    ApplicationOverview,
    count_open_by_severity,
    is_sbom_stale,
    scan_state,
)
from app.domain.inventory import Application
from app.domain.remediation import compute_deadlines
from app.domain.vulnerability import Finding, is_closed


@dataclass(frozen=True)
class _Snapshot:
    """Alles, was die Übersicht braucht, je einmal für alle Anwendungen geladen."""

    findings: dict[int, list[Finding]]
    active_components: dict[int, int]
    latest_sbom: dict[int, datetime]
    last_scan_started_at: datetime | None
    now: datetime


class GetApplicationsOverview:
    def __init__(self, uow: UnitOfWork, clock: Callable[[], datetime]) -> None:
        self._uow = uow
        self._clock = clock

    def execute(self) -> list[ApplicationOverview]:
        snapshot = self._snapshot()
        applications = sorted(
            self._uow.applications.list(), key=lambda application: application.name
        )
        return [_overview_of(application, snapshot) for application in applications]

    def _snapshot(self) -> _Snapshot:
        # Funde aller Stufen gruppiert; auch ausgebaute Komponenten zählen wie in der Detailansicht.
        findings: dict[int, list[Finding]] = defaultdict(list)
        for finding in self._uow.findings.list():
            findings[finding.application_id].append(finding)
        active: dict[int, int] = defaultdict(int)
        for component in self._uow.components.list_all():
            if component.application_id is not None and not component.is_retired:
                active[component.application_id] += 1
        last_scan = self._uow.scan_runs.latest_usable()
        return _Snapshot(
            findings=findings,
            active_components=active,
            latest_sbom=self._uow.sboms.latest_upload_by_application(),
            last_scan_started_at=last_scan.started_at if last_scan else None,
            now=self._clock(),
        )


def _overview_of(application: Application, snapshot: _Snapshot) -> ApplicationOverview:
    assert application.id is not None
    findings = snapshot.findings.get(application.id, [])
    open_findings = [finding for finding in findings if not is_closed(finding.status)]
    latest_sbom = snapshot.latest_sbom.get(application.id)
    return ApplicationOverview(
        application_id=application.id,
        name=application.name,
        description=application.description,
        open_by_severity=count_open_by_severity(open_findings),
        overdue=compute_deadlines(open_findings, snapshot.now).overdue,
        component_count=snapshot.active_components.get(application.id, 0),
        latest_sbom_upload_at=latest_sbom,
        sbom_stale=is_sbom_stale(latest_sbom, snapshot.now),
        scan_state=scan_state(application.inventory_changed_at, snapshot.last_scan_started_at),
        inventory_changed_at=application.inventory_changed_at,
        github_repository=application.github_repository,
    )
