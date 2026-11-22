"""Router zum Starten des Ingests im Hintergrund und Abfragen seines Zustands.

Den Runner setzt der Composition Root (app/main.py) als ``app.state.ingest_runner``.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.application.ingest_runner import IngestRunner, IngestRunState
from app.application.scan_runs import GetScanHistory, ScanHistory
from app.domain.scan_run import ScanOutcome, ScanRun, ScanTrigger
from app.presentation.dependencies import UnitOfWorkDep
from app.presentation.schemas import ApiModel

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

ALREADY_RUNNING = "Ein Scan läuft bereits"


def get_ingest_runner(request: Request) -> IngestRunner:
    runner: IngestRunner = request.app.state.ingest_runner
    return runner


RunnerDep = Annotated[IngestRunner, Depends(get_ingest_runner)]


class ScanRunResponse(ApiModel):
    trigger: ScanTrigger
    outcome: ScanOutcome | None
    started_at: datetime
    finished_at: datetime | None
    components_scanned: int | None
    findings_found: int | None
    sources_with_errors: int
    message: str


class IngestStateResponse(ApiModel):
    running: bool
    started_at: datetime | None
    finished_at: datetime | None
    components_scanned: int | None
    findings_found: int | None
    error: str | None
    last_run: ScanRunResponse | None
    last_usable_run: ScanRunResponse | None


def _run_response(run: ScanRun | None) -> ScanRunResponse | None:
    if run is None:
        return None
    return ScanRunResponse(
        trigger=run.trigger,
        outcome=run.outcome,
        started_at=run.started_at,
        finished_at=run.finished_at,
        components_scanned=run.components_scanned,
        findings_found=run.findings_found,
        sources_with_errors=run.sources_with_errors,
        message=run.message,
    )


def _to_response(state: IngestRunState, history: ScanHistory) -> IngestStateResponse:
    return IngestStateResponse(
        running=state.running,
        started_at=state.started_at,
        finished_at=state.finished_at,
        components_scanned=state.components_scanned,
        findings_found=state.findings_found,
        error=state.error,
        last_run=_run_response(history.last_run),
        last_usable_run=_run_response(history.last_usable_run),
    )


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
def start_ingest(runner: RunnerDep, uow: UnitOfWorkDep) -> IngestStateResponse:
    if not runner.start():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ALREADY_RUNNING)
    return _to_response(runner.state(), GetScanHistory(uow).execute())


@router.get("/status")
def ingest_status(runner: RunnerDep, uow: UnitOfWorkDep) -> IngestStateResponse:
    return _to_response(runner.state(), GetScanHistory(uow).execute())
