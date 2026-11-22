"""Use Case: GitHub-Repository und Automatik-Schwelle einer Anwendung pflegen."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.application.unit_of_work import UnitOfWork
from app.domain.errors import InvalidValueError
from app.domain.inventory import Application, is_valid_github_repository
from app.domain.vulnerability import Severity

INVALID_REPOSITORY_MESSAGE = "Repository als owner/repo angeben (z. B. acme/shop)"


@dataclass(frozen=True)
class GitHubSettingsChange:
    """Nur die Felder mit ``set_*`` werden übernommen; ``None`` entfernt den Wert."""

    repository: str | None = None
    min_level: Severity | None = None
    set_repository: bool = False
    set_min_level: bool = False


class UpdateGitHubSettings:
    def __init__(self, uow: UnitOfWork, clock: Callable[[], datetime]) -> None:
        self._uow = uow
        self._clock = clock

    def execute(self, application_id: int, change: GitHubSettingsChange) -> None:
        application = self._uow.applications.get(application_id)  # EntityNotFoundError
        if change.set_repository:
            if change.repository is not None and not is_valid_github_repository(change.repository):
                raise InvalidValueError(INVALID_REPOSITORY_MESSAGE)
            application.github_repository = change.repository
        if change.set_min_level:
            self._change_threshold(application, change.min_level)
        self._uow.applications.update(application)
        self._uow.commit()

    def _change_threshold(self, application: Application, level: Severity | None) -> None:
        if level != application.auto_issue_min_level:
            application.auto_issue_enabled_at = self._clock() if level else None
        application.auto_issue_min_level = level
