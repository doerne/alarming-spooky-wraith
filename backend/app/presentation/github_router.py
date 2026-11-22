"""Router für den GitHub-Abgleich: Status, Start per Button. Enthält keine Fachlogik."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.application.github_start import (
    NOT_CONFIGURED_MESSAGE,
    StartGitHubSync,
)
from app.application.github_sync import GitHubSyncRunner, SyncRunState
from app.domain.ports import IssueTracker
from app.domain.vulnerability import Severity
from app.presentation.dependencies import UnitOfWorkDep
from app.presentation.schemas import ApiModel

router = APIRouter(prefix="/api", tags=["github"])

NOT_CONFIGURED = NOT_CONFIGURED_MESSAGE


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
    if tracker is None or runner is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=NOT_CONFIGURED)
    state = StartGitHubSync(uow, tracker, runner).execute(
        application_id, body.create_issues, body.min_level
    )
    return _to_state_response(state)
