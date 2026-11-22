"""Use Case: GitHub-Issues für offene CVEs anlegen und den Status mit CVE-Radar abgleichen."""

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.application.issue_export import ExportApplicationIssues, IssueDraft
from app.application.issue_sync_rules import IssueAction, aggregate_state, decide_issue_action
from app.application.unit_of_work import UnitOfWork, UnitOfWorkFactory
from app.domain.errors import IssueTrackerError
from app.domain.inventory import Application
from app.domain.ports import AdvisoryStore, IssueContent, IssueTracker, TrackedIssue
from app.domain.vulnerability import (
    Finding,
    FindingStatus,
    IssueState,
    ResolutionSource,
    Severity,
    severity_rank,
)

_logger = logging.getLogger(__name__)
_OPEN_STATUSES = frozenset({FindingStatus.OPEN, FindingStatus.IN_PROGRESS})
_RATED_STATUSES = frozenset({FindingStatus.ACCEPTED, FindingStatus.FALSE_POSITIVE})
_MARK_ACTIONS = frozenset(
    {
        IssueAction.MARK_FIXED,
        IssueAction.MARK_CLOSED_EXTERNALLY_COMPLETED,
        IssueAction.MARK_ACCEPTED,
    }
)
_CLOSE_ACTIONS = frozenset({IssueAction.CLOSE_COMPLETED, IssueAction.CLOSE_NOT_PLANNED})
_REOPEN_ACTIONS = frozenset({IssueAction.REOPEN, IssueAction.REOPEN_ISSUE})
_MAX_MESSAGE_LENGTH = 500


class IssueFormatter(Protocol):
    """Erzeugt Titel, Text, Labels und Marker eines Issues aus einem Entwurf."""

    def format(self, application_id: int, draft: IssueDraft) -> IssueContent: ...


@dataclass(frozen=True)
class SyncRequest:
    application_id: int | None  # None = alle Anwendungen mit Repository
    create_issues: bool  # Button „Issues anlegen“
    min_level: Severity | None  # Mindest-Risiko für den Button


@dataclass(frozen=True)
class SyncOutcome:
    application_id: int
    message: str


@dataclass(frozen=True)
class _LinkedIssue:
    """Ein GitHub-Issue und die Treffer einer CVE, die daran hängen."""

    repository: str
    number: int
    url: str
    group: list[Finding]
    active: list[Finding]
    retired: list[Finding]


@dataclass
class _Counts:
    created: int = 0
    linked: int = 0
    closed: int = 0
    reopened: int = 0
    notes: list[str] | None = None

    def note(self, text: str) -> None:
        self.notes = [*(self.notes or []), text]

    def summary(self) -> str:
        parts = [
            f"{count} {label}"
            for count, label in (
                (self.created, "angelegt"),
                (self.closed, "geschlossen"),
                (self.linked, "verknüpft"),
                (self.reopened, "wieder geöffnet"),
            )
            if count
        ]
        parts += self.notes or []
        return ", ".join(parts) or "Keine Änderungen"


class SyncGitHubIssues:
    def __init__(
        self,
        uow: UnitOfWork,
        tracker: IssueTracker,
        formatter: IssueFormatter,
        drafts: ExportApplicationIssues,
        clock: Callable[[], datetime],
    ) -> None:
        self._uow = uow
        self._tracker = tracker
        self._formatter = formatter
        self._drafts = drafts
        self._clock = clock

    def execute(self, request: SyncRequest) -> list[SyncOutcome]:
        if not self._tracker.is_configured():
            raise IssueTrackerError("GitHub ist nicht konfiguriert")
        outcomes: list[SyncOutcome] = []
        for application in self._targets(request.application_id):
            assert application.id is not None
            outcomes.append(self._sync_application(application.id, request))
        return outcomes

    def _targets(self, application_id: int | None) -> list[Application]:
        if application_id is None:
            applications = self._uow.applications.list()
        else:
            applications = [self._uow.applications.get(application_id)]
        return [application for application in applications if application.github_repository]

    def _sync_application(self, application_id: int, request: SyncRequest) -> SyncOutcome:
        try:
            message = self._sync_one(application_id, request)
            self._uow.commit()
        except IssueTrackerError as error:
            return self._record_failure(application_id, str(error))
        except Exception as error:  # je Anwendung isolieren; Details nur ins Log
            _logger.exception("GitHub-Abgleich fehlgeschlagen")
            failure = f"Abgleich fehlgeschlagen ({type(error).__name__})"
            return self._record_failure(application_id, failure)
        return SyncOutcome(application_id, message)

    def _record_failure(self, application_id: int, message: str) -> SyncOutcome:
        self._uow.rollback()
        self._store_message(self._uow.applications.get(application_id), message)
        self._uow.commit()
        return SyncOutcome(application_id, message)

    def _store_message(self, application: Application, message: str) -> None:
        application.github_sync_message = message[:_MAX_MESSAGE_LENGTH]
        application.github_synced_at = self._clock()
        self._uow.applications.update(application)

    def _sync_one(self, application_id: int, request: SyncRequest) -> str:
        application = self._uow.applications.get(application_id)
        repository = application.github_repository
        assert repository is not None
        counts = _Counts()
        self._sync_linked_issues(application_id, repository, counts)
        self._create_missing(application, request, counts)
        message = counts.summary()
        self._store_message(application, message)
        return message

    # --- Abgleich bestehender Verknüpfungen ---------------------------------

    def _sync_linked_issues(self, application_id: int, repository: str, counts: _Counts) -> None:
        pattern = re.compile(rf"^https://github\.com/{re.escape(repository)}/issues/(\d+)$")
        retired_ids = {
            component.id
            for component in self._uow.components.list_for_application(application_id)
            if component.is_retired
        }
        for group in _group_by_advisory(self._application_findings(application_id)):
            link = _find_link(group, pattern)
            if link is None:
                continue
            url, number = link
            active = [item for item in group if item.component_id not in retired_ids]
            retired = [item for item in group if item.component_id in retired_ids]
            linked = _LinkedIssue(repository, number, url, group, active, retired)
            self._sync_issue(linked, counts)

    def _application_findings(self, application_id: int) -> list[Finding]:
        return [item for item in self._uow.findings.list() if item.application_id == application_id]

    def _sync_issue(self, linked: _LinkedIssue, counts: _Counts) -> None:
        live = self._tracker.get(linked.repository, linked.number)
        if live is None:
            counts.note(f"Issue #{linked.number} nicht gefunden")
            return
        action = decide_issue_action(
            linked.group[0].issue_state,
            live,
            aggregate_state(linked.active, linked.retired),
            has_fix_evidence=any(
                item.status == FindingStatus.FIXED and item.resolved_by == ResolutionSource.SBOM
                for item in linked.group
            ),
        )
        self._apply(action, linked)
        _count(action, counts)
        state = _resulting_state(action, live)
        for finding in linked.group:
            assert finding.id is not None
            self._uow.findings.save_issue_link(finding.id, linked.url, state)

    def _apply(self, action: IssueAction, linked: _LinkedIssue) -> None:
        if action in _MARK_ACTIONS:
            self._mark_findings(action, linked)
        elif action in _CLOSE_ACTIONS:
            self._close_issue(action, linked)
        elif action == IssueAction.REOPEN:
            self._reopen_findings(linked)
        elif action == IssueAction.REOPEN_ISSUE:
            comment = _last_open_note(linked.group)
            self._tracker.set_open(linked.repository, linked.number, True, comment)

    def _mark_findings(self, action: IssueAction, linked: _LinkedIssue) -> None:
        if action == IssueAction.MARK_ACCEPTED:
            note = f"Issue #{linked.number} als not planned geschlossen"
            for finding in _open_findings(linked.active):
                accepted = finding.with_note(note).with_status(
                    FindingStatus.ACCEPTED, self._clock()
                )
                self._uow.findings.save_report(accepted)
            return
        text = f"Issue #{linked.number} geschlossen"
        for finding in _open_findings(linked.active):
            assert finding.id is not None
            resolution = finding.resolution_for(
                FindingStatus.FIXED, self._clock(), text, ResolutionSource.REPORTED
            )
            self._uow.findings.resolve(finding.id, resolution)

    def _close_issue(self, action: IssueAction, linked: _LinkedIssue) -> None:
        if action == IssueAction.CLOSE_COMPLETED:
            comment = _behoben_comment(linked.group)
            self._tracker.set_open(linked.repository, linked.number, False, comment)
            return
        comment = f"In CVE-Radar als {_rated_status(linked.group)} bewertet"
        self._tracker.set_open(linked.repository, linked.number, False, comment, True)

    def _reopen_findings(self, linked: _LinkedIssue) -> None:
        note = f"Issue #{linked.number} wieder geöffnet"
        for finding in linked.active:
            if finding.status not in _OPEN_STATUSES:
                self._uow.findings.save_report(finding.reopened().with_note(note))

    # --- Anlegen ------------------------------------------------------------

    def _create_missing(
        self, application: Application, request: SyncRequest, counts: _Counts
    ) -> None:
        threshold = _threshold(application, request)
        repository = application.github_repository
        assert application.id is not None
        assert repository is not None
        if threshold is None:
            return
        automatic = not request.create_issues
        candidates = [
            draft
            for draft in self._drafts.execute(application.id).issues
            if self._is_candidate(draft, threshold, application, automatic)
        ]
        if not candidates:
            return
        existing = self._tracker.existing_markers(repository)
        for draft in candidates:
            content = self._formatter.format(application.id, draft)
            issue = existing.get(content.marker)
            if issue is None:
                issue = self._tracker.create(repository, content)
                counts.created += 1
            else:
                counts.linked += 1
            self._link_open_findings(application.id, draft.advisory_id, issue)

    def _is_candidate(
        self, draft: IssueDraft, threshold: Severity, application: Application, automatic: bool
    ) -> bool:
        if draft.issue_urls:
            return False
        if severity_rank(draft.risk_level) < severity_rank(threshold):
            return False
        return not automatic or self._seen_after_enable(draft.advisory_id, application)

    def _seen_after_enable(self, advisory_id: str, application: Application) -> bool:
        enabled_at = application.auto_issue_enabled_at
        if enabled_at is None or application.id is None:
            return False
        seen = [
            item.first_seen_at
            for item in self._application_findings(application.id)
            if item.advisory_id == advisory_id and item.first_seen_at is not None
        ]
        return bool(seen) and max(seen) >= enabled_at

    def _link_open_findings(
        self, application_id: int, advisory_id: str, issue: TrackedIssue
    ) -> None:
        state = IssueState.OPEN if issue.is_open else IssueState.CLOSED
        for finding in self._application_findings(application_id):
            if finding.advisory_id == advisory_id and finding.status in _OPEN_STATUSES:
                assert finding.id is not None
                self._uow.findings.save_issue_link(finding.id, issue.url, state)


def _threshold(application: Application, request: SyncRequest) -> Severity | None:
    if request.create_issues:
        return request.min_level or Severity.NIEDRIG
    return application.auto_issue_min_level


def _group_by_advisory(findings: list[Finding]) -> list[list[Finding]]:
    groups: dict[str, list[Finding]] = {}
    for finding in findings:
        groups.setdefault(finding.advisory_id, []).append(finding)
    return list(groups.values())


def _find_link(group: list[Finding], pattern: re.Pattern[str]) -> tuple[str, int] | None:
    for finding in group:
        match = pattern.match(finding.issue_url)
        if match:
            return finding.issue_url, int(match.group(1))
    return None


def _open_findings(findings: list[Finding]) -> list[Finding]:
    return [finding for finding in findings if finding.status in _OPEN_STATUSES]


def _resulting_state(action: IssueAction, live: TrackedIssue) -> IssueState:
    if action in _CLOSE_ACTIONS:
        return IssueState.CLOSED
    if action == IssueAction.REOPEN_ISSUE:
        return IssueState.OPEN
    return IssueState.OPEN if live.is_open else IssueState.CLOSED


def _count(action: IssueAction, counts: _Counts) -> None:
    if action in _MARK_ACTIONS or action in _CLOSE_ACTIONS:
        counts.closed += 1
    elif action in _REOPEN_ACTIONS:
        counts.reopened += 1


def _behoben_comment(group: list[Finding]) -> str:
    resolution = next(
        (
            item.resolution
            for item in group
            if item.status == FindingStatus.FIXED and item.resolved_by == ResolutionSource.SBOM
        ),
        "",
    )
    return f"Behoben: {resolution or 'SBOM-Nachweis'}"


def _rated_status(group: list[Finding]) -> str:
    rated = next((item.status for item in group if item.status in _RATED_STATUSES), None)
    return (rated or FindingStatus.ACCEPTED).value


def _last_open_note(group: list[Finding]) -> str:
    return next(
        (
            item.comment
            for item in reversed(group)
            if item.status in _OPEN_STATUSES and item.comment
        ),
        "Wieder offen in CVE-Radar",
    )


@dataclass(frozen=True)
class SyncRunState:
    """Zustand des letzten bzw. laufenden Abgleichs im Hintergrund."""

    running: bool
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None


class GitHubSyncRunner(Protocol):
    def start(self, request: SyncRequest) -> bool:
        """Startet einen Abgleich. False, wenn ein Scan oder Abgleich läuft."""
        ...

    def state(self) -> SyncRunState: ...


@dataclass(frozen=True)
class GitHubSyncServices:
    """Abhängigkeiten des Abgleichs, vom Composition Root gesetzt."""

    tracker: IssueTracker
    formatter: IssueFormatter
    store: AdvisoryStore
    clock: Callable[[], datetime]


def run_github_sync(
    uow_factory: UnitOfWorkFactory, services: GitHubSyncServices, request: SyncRequest
) -> bool:
    """Abgleich mit eigener Unit of Work; ohne GitHub-Konfiguration passiert nichts (False)."""
    if not services.tracker.is_configured():
        return False
    with uow_factory() as uow:
        drafts = ExportApplicationIssues(uow, services.store, services.clock)
        SyncGitHubIssues(uow, services.tracker, services.formatter, drafts, services.clock).execute(
            request
        )
    return True
