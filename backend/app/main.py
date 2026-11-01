"""Composition Root: der einzige Ort, der alle Schichten kennt und verdrahtet."""

from datetime import UTC, datetime
from functools import partial

import httpx
from fastapi import FastAPI

from app.application.component_matching import ComponentMatcher
from app.application.ingest import IngestResult, RunIngest
from app.application.source_registry import SourceRegistry
from app.application.unit_of_work import UnitOfWork
from app.domain.ports import AdvisoryStore
from app.infrastructure.config import get_settings
from app.infrastructure.database import create_session_factory
from app.infrastructure.okf_store import FileAdvisoryStore
from app.infrastructure.osv_client import HttpxOsvClient
from app.infrastructure.unit_of_work import sqlalchemy_unit_of_work
from app.infrastructure.univers_matcher import UniversVersionMatcher
from app.presentation.app_factory import create_app


def _now() -> datetime:
    return datetime.now(UTC)


def _run_ingest(
    registry: SourceRegistry, matcher: ComponentMatcher, store: AdvisoryStore, uow: UnitOfWork
) -> IngestResult:
    return RunIngest(uow, registry, matcher, store, _now).execute()


def build_app() -> FastAPI:
    settings = get_settings()
    session_factory = create_session_factory(settings.sqlalchemy_url())
    registry = SourceRegistry([HttpxOsvClient(settings.osv_base_url, httpx.Client(timeout=30.0))])
    matcher = ComponentMatcher(UniversVersionMatcher())
    store = FileAdvisoryStore(settings.okf_root)
    return create_app(
        partial(sqlalchemy_unit_of_work, session_factory),
        enable_docs=settings.enable_docs,
        run_ingest=partial(_run_ingest, registry, matcher, store),
        source_registry=registry,
    )


app = build_app()
