from fastapi import FastAPI

from app.application.unit_of_work import UnitOfWorkFactory
from app.presentation.error_handlers import register_error_handlers
from app.presentation.health_router import router as health_router


def create_app(uow_factory: UnitOfWorkFactory, *, enable_docs: bool = False) -> FastAPI:
    """Baut die HTTP-App. Die Persistenz wird von außen hineingereicht."""
    app = FastAPI(
        title="alarming-spooky-wraith API",
        docs_url="/api/docs" if enable_docs else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if enable_docs else None,
    )
    app.state.uow_factory = uow_factory
    register_error_handlers(app)
    app.include_router(health_router)
    # Neue Feature-Router hier einbinden: app.include_router(orders_router)
    return app
