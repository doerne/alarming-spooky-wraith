"""Use Case: GitHub-Abgleich per Knopf starten; Vorbedingungen als Domain-Fehler."""

from app.application.github_sync import GitHubSyncRunner, SyncRequest, SyncRunState
from app.application.unit_of_work import UnitOfWork
from app.domain.errors import ConflictError, IssueTrackerError
from app.domain.ports import IssueTracker
from app.domain.vulnerability import Severity

NO_REPOSITORY_MESSAGE = "Für diese Anwendung ist kein GitHub-Repository hinterlegt"
NOT_CONFIGURED_MESSAGE = "GitHub ist nicht konfiguriert"
ALREADY_RUNNING_MESSAGE = "Ein Scan oder Abgleich läuft bereits"


class StartGitHubSync:
    def __init__(self, uow: UnitOfWork, tracker: IssueTracker, runner: GitHubSyncRunner) -> None:
        self._uow = uow
        self._tracker = tracker
        self._runner = runner

    def execute(
        self, application_id: int, create_issues: bool, min_level: Severity | None
    ) -> SyncRunState:
        application = self._uow.applications.get(application_id)  # EntityNotFoundError
        if application.github_repository is None:
            raise ConflictError(NO_REPOSITORY_MESSAGE)
        if not self._tracker.is_configured():
            raise IssueTrackerError(NOT_CONFIGURED_MESSAGE)
        request = SyncRequest(application_id, create_issues=create_issues, min_level=min_level)
        if not self._runner.start(request):
            raise ConflictError(ALREADY_RUNNING_MESSAGE)
        return self._runner.state()
