"""Router für den GitHub-Abgleich: Status, Start per Button. Enthält keine Fachlogik."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.application.github_sync import GitHubSyncRunner, SyncRequest, SyncRunState
from app.domain.ports import IssueTracker
from app.domain.vulnerability import Severity
from app.presentation.dependencies import UnitOfWorkDep
from app.presentation.schemas import ApiModel

router = APIRouter(prefix="/api", tags=["github"])

ALREADY_RUNNING = "Ein Scan oder Abgleich läuft bereits"
NOT_CONFIGURED = "GitHub ist nicht konfiguriert"
NO_REPOSITORY = "Für diese Anwendung ist kein GitHub-Repository hinterlegt"


def get_tracker(request: Request) -> IssueTracker | None:
    tracker: IssueTracker | None = request.app.state.github_tracker
    return tracker


def get_sync_runner(request: Request) -> GitHubSyncRunner | None:
    runner: GitHubSyncRunner | None = request.app.state.github_sync_runner
    return runner


TrackerDep = Annotated[IssueTracker | None, Depends(get_tracker)]
SyncRunnerDep = Annotated[GitHubSyncRunner | None, Depends(get_sync_runner)]


class GitHubStatusResponse(ApiModel):
    configured: bool
    running: bool


class GitHubSyncBody(ApiModel):
    create_issues: bool = False
    min_level: Severity | None = None


class GitHubSyncStateResponse(ApiModel):
    running: bool
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None


def _to_state_response(state: SyncRunState) -> GitHubSyncStateResponse:
    return GitHubSyncStateResponse(
        running=state.running,
        started_at=state.started_at,
        finished_at=state.finished_at,
        error=state.error,
    )


@router.get("/github/status")
def github_status(tracker: TrackerDep, runner: SyncRunnerDep) -> GitHubStatusResponse:
    return GitHubStatusResponse(
        configured=tracker is not None and tracker.is_configured(),
        running=runner is not None and runner.state().running,
    )


@router.post("/applications/{application_id}/github/sync", status_code=status.HTTP_202_ACCEPTED)
def start_github_sync(
    application_id: int,
    body: GitHubSyncBody,
    uow: UnitOfWorkDep,
    tracker: TrackerDep,
    runner: SyncRunnerDep,
) -> GitHubSyncStateResponse:
    application = uow.applications.get(application_id)  # EntityNotFoundError → 404
    if application.github_repository is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=NO_REPOSITORY)
    if tracker is None or runner is None or not tracker.is_configured():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=NOT_CONFIGURED)
    request = SyncRequest(
        application_id, create_issues=body.create_issues, min_level=body.min_level
    )
    if not runner.start(request):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ALREADY_RUNNING)
    return _to_state_response(runner.state())
