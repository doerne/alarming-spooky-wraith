"""Router zum Auslösen des Ingests.

Die Ausführung (Quellen, Abgleich, Ablage) setzt der Composition Root
(app/main.py) als ``app.state.run_ingest``.
"""

from collections.abc import Callable

from fastapi import APIRouter, Request

from app.application.ingest import IngestResult
from app.application.unit_of_work import UnitOfWork
from app.presentation.dependencies import UnitOfWorkDep
from app.presentation.schemas import ApiModel

router = APIRouter(prefix="/api", tags=["ingest"])


class IngestResultResponse(ApiModel):
    components_scanned: int
    findings_found: int


@router.post("/ingest/run")
def run_ingest(request: Request, uow: UnitOfWorkDep) -> IngestResultResponse:
    execute: Callable[[UnitOfWork], IngestResult] = request.app.state.run_ingest
    result = execute(uow)
    return IngestResultResponse(
        components_scanned=result.components_scanned,
        findings_found=result.findings_found,
    )
