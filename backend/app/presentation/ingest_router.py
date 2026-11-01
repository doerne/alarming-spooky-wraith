"""Router zum Starten des Ingests im Hintergrund und Abfragen seines Zustands.

Den Runner setzt der Composition Root (app/main.py) als ``app.state.ingest_runner``.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.application.ingest_runner import IngestRunner, IngestRunState
from app.presentation.schemas import ApiModel

router = APIRouter(prefix="/api/ingest", tags=["ingest"])

ALREADY_RUNNING = "Ein Scan läuft bereits"


def get_ingest_runner(request: Request) -> IngestRunner:
    runner: IngestRunner = request.app.state.ingest_runner
    return runner


RunnerDep = Annotated[IngestRunner, Depends(get_ingest_runner)]


class IngestStateResponse(ApiModel):
    running: bool
    started_at: datetime | None
    finished_at: datetime | None
    components_scanned: int | None
    findings_found: int | None
    error: str | None


def _to_response(state: IngestRunState) -> IngestStateResponse:
    return IngestStateResponse(
        running=state.running,
        started_at=state.started_at,
        finished_at=state.finished_at,
        components_scanned=state.components_scanned,
        findings_found=state.findings_found,
        error=state.error,
    )


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
def start_ingest(runner: RunnerDep) -> IngestStateResponse:
    if not runner.start():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ALREADY_RUNNING)
    return _to_response(runner.state())


@router.get("/status")
def ingest_status(runner: RunnerDep) -> IngestStateResponse:
    return _to_response(runner.state())
