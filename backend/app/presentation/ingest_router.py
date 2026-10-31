"""Router zum Ausloesen des Ingests.

Stufe 1: synchron. Spaeter legt der Endpoint nur einen Job in die Queue.
Die OsvClient- und AdvisoryStore-Instanzen setzt der Composition Root
(app/main.py) in app.state.
"""

from fastapi import APIRouter, Request

from app.application.ingest import RunIngest
from app.domain.ports import AdvisoryStore, OsvClient
from app.presentation.dependencies import UnitOfWorkDep
from app.presentation.schemas import ApiModel

router = APIRouter(prefix="/api", tags=["ingest"])


class IngestResultResponse(ApiModel):
    components_scanned: int
    findings_found: int


@router.post("/ingest/run")
def run_ingest(request: Request, uow: UnitOfWorkDep) -> IngestResultResponse:
    osv: OsvClient = request.app.state.osv_client
    store: AdvisoryStore = request.app.state.advisory_store
    result = RunIngest(uow, osv, store).execute()
    return IngestResultResponse(
        components_scanned=result.components_scanned,
        findings_found=result.findings_found,
    )
