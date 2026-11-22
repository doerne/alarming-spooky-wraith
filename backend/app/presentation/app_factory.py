from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from datetime import datetime

from fastapi import FastAPI

from app.application.github_sync import GitHubSyncRunner
from app.application.ingest_runner import IngestRunner
from app.application.source_registry import SourceRegistry
from app.application.unit_of_work import UnitOfWorkFactory
from app.domain.ports import AdvisoryStore, IssueTracker, SbomParser, VersionComparator
from app.presentation.cves_router import router as cves_router
from app.presentation.error_handlers import register_error_handlers
from app.presentation.github_router import router as github_router
from app.presentation.health_router import router as health_router
from app.presentation.ingest_router import router as ingest_router
from app.presentation.inventory_router import router as inventory_router
from app.presentation.kpis_router import router as kpis_router
from app.presentation.sbom_router import router as sbom_router
from app.presentation.sources_router import router as sources_router
from app.presentation.trend_router import router as trend_router


def _lifespan(
    on_startup: Callable[[], None] | None,
    on_shutdown: Callable[[], None] | None,
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if on_startup is not None:
            on_startup()
        yield
        if on_shutdown is not None:
            on_shutdown()

    return lifespan


@dataclass(frozen=True)
class AppServices:
    """Vom Composition Root eingereichte Dienste (Tests setzen nur, was sie brauchen)."""

    ingest_runner: IngestRunner | None = None
    advisory_store: AdvisoryStore | None = None
    source_registry: SourceRegistry | None = None
    on_startup: Callable[[], None] | None = None
    on_shutdown: Callable[[], None] | None = None
    sbom_parser: SbomParser | None = None
    clock: Callable[[], datetime] | None = None
    github_tracker: IssueTracker | None = None
    github_sync_runner: GitHubSyncRunner | None = None
    version_comparator: VersionComparator | None = None


def create_app(
    uow_factory: UnitOfWorkFactory,
    *,
    enable_docs: bool = False,
    services: AppServices | None = None,
) -> FastAPI:
    """Baut die HTTP-App. Persistenz und Datenquellen werden hineingereicht."""
    services = services or AppServices()
    app = FastAPI(
        title="alarming-spooky-wraith API",
        docs_url="/api/docs" if enable_docs else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if enable_docs else None,
        lifespan=_lifespan(services.on_startup, services.on_shutdown),
    )
    app.state.uow_factory = uow_factory
    app.state.ingest_runner = services.ingest_runner
    app.state.advisory_store = services.advisory_store
    app.state.source_registry = services.source_registry
    app.state.sbom_parser = services.sbom_parser
    app.state.clock = services.clock
    app.state.github_tracker = services.github_tracker
    app.state.github_sync_runner = services.github_sync_runner
    app.state.version_comparator = services.version_comparator
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(inventory_router)
    app.include_router(sbom_router)
    app.include_router(ingest_router)
    app.include_router(cves_router)
    app.include_router(trend_router)
    app.include_router(kpis_router)
    app.include_router(sources_router)
    app.include_router(github_router)
    return app
