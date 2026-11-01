from collections.abc import Callable

from fastapi import FastAPI

from app.application.ingest import IngestResult
from app.application.source_registry import SourceRegistry
from app.application.unit_of_work import UnitOfWork, UnitOfWorkFactory
from app.presentation.cves_router import router as cves_router
from app.presentation.error_handlers import register_error_handlers
from app.presentation.health_router import router as health_router
from app.presentation.ingest_router import router as ingest_router
from app.presentation.inventory_router import router as inventory_router
from app.presentation.sources_router import router as sources_router


def create_app(
    uow_factory: UnitOfWorkFactory,
    *,
    enable_docs: bool = False,
    run_ingest: Callable[[UnitOfWork], IngestResult] | None = None,
    source_registry: SourceRegistry | None = None,
) -> FastAPI:
    """Baut die HTTP-App. Persistenz und Datenquellen werden hineingereicht."""
    app = FastAPI(
        title="alarming-spooky-wraith API",
        docs_url="/api/docs" if enable_docs else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if enable_docs else None,
    )
    app.state.uow_factory = uow_factory
    app.state.run_ingest = run_ingest
    app.state.source_registry = source_registry
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(inventory_router)
    app.include_router(ingest_router)
    app.include_router(cves_router)
    app.include_router(sources_router)
    return app
