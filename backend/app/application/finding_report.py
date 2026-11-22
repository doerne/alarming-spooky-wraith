"""Use Case: ein Agent meldet Issue-URL, Status oder Kommentar zu einer CVE einer Anwendung."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime

from app.application.unit_of_work import UnitOfWork
from app.domain.errors import EntityNotFoundError
from app.domain.vulnerability import Finding, FindingStatus, ResolutionSource


@dataclass(frozen=True)
class ProgressReport:
    """Was der Agent meldet; nicht gesetzte Felder bleiben unverändert."""

    status: FindingStatus | None = None
    issue_url: str | None = None
    comment: str | None = None


def _reported_resolution(issue_url: str) -> str:
    return f"Als behoben gemeldet (Issue {issue_url})" if issue_url else "Als behoben gemeldet"


def _with_status(finding: Finding, status: FindingStatus, now: datetime) -> Finding:
    if status == FindingStatus.FIXED and finding.status == FindingStatus.FIXED:
        # Schon behoben (ggf. per SBOM nachgewiesen): Nachweis und Zeitpunkt bleiben.
        return finding
    if status != FindingStatus.FIXED:
        return replace(finding.reopened(), status=status)
    # Vorläufig: der nächste SBOM-Upload prüft nach (siehe UploadSbomVersion).
    return replace(
        finding,
        status=status,
        resolved_at=now,
        resolved_by=ResolutionSource.REPORTED,
        resolution=_reported_resolution(finding.issue_url),
    )


def _apply(finding: Finding, report: ProgressReport, now: datetime) -> Finding:
    updated = finding
    if report.issue_url is not None:
        updated = replace(updated, issue_url=report.issue_url)
    if report.comment:
        updated = updated.with_note(report.comment)
    if report.status is not None:
        updated = _with_status(updated, report.status, now)
    return updated


class ReportFindingProgress:
    def __init__(self, uow: UnitOfWork, clock: Callable[[], datetime]) -> None:
        self._uow = uow
        self._clock = clock

    def execute(
        self, *, application_id: int, advisory_id: str, report: ProgressReport
    ) -> tuple[str, int]:
        """Wirkt auf alle Treffer der Anwendung zu dieser Advisory; (kanonische ID, Anzahl)."""
        self._uow.applications.get(application_id)  # EntityNotFoundError
        canonical_id = self._canonical(advisory_id)
        findings = [
            finding
            for finding in self._uow.findings.list_for_advisory(canonical_id)
            if finding.application_id == application_id
        ]
        if not findings:
            raise EntityNotFoundError("CVE der Anwendung", advisory_id)
        now = self._clock()
        for finding in findings:
            if self._uow.components.get(finding.component_id).is_retired:
                # Historie ausgebauter Komponenten: nur den Issue-Link ergänzen.
                if report.issue_url is not None:
                    self._uow.findings.save_report(replace(finding, issue_url=report.issue_url))
                continue
            self._uow.findings.save_report(_apply(finding, report, now))
        self._uow.commit()
        return canonical_id, len(findings)

    def _canonical(self, advisory_id: str) -> str:
        """Alte Marker nennen ggf. eine inzwischen zusammengeführte ID."""
        if self._uow.advisories.find(advisory_id) is not None:
            return advisory_id
        return self._uow.advisory_aliases.resolve(advisory_id) or advisory_id
