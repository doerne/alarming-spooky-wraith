"""Composition Root: der einzige Ort, der alle Schichten kennt und verdrahtet."""

from datetime import UTC, datetime
from functools import partial

import httpx
from fastapi import FastAPI

from app.application.component_matching import ComponentMatcher
from app.application.ingest import run_ingest_job
from app.application.source_registry import SourceRegistry
from app.application.source_use_cases import reset_interrupted_runs
from app.infrastructure.config import get_settings
from app.infrastructure.database import create_session_factory
from app.infrastructure.okf_store import FileAdvisoryStore
from app.infrastructure.sources.osv import OsvSource
from app.infrastructure.thread_ingest_runner import ThreadIngestRunner
from app.infrastructure.unit_of_work import sqlalchemy_unit_of_work
from app.infrastructure.univers_matcher import UniversVersionMatcher
from app.presentation.app_factory import create_app


def _now() -> datetime:
    return datetime.now(UTC)


def build_app() -> FastAPI:
    settings = get_settings()
    uow_factory = partial(
        sqlalchemy_unit_of_work, create_session_factory(settings.sqlalchemy_url())
    )
    registry = SourceRegistry([OsvSource(settings.osv_base_url, httpx.Client(timeout=30.0))])
    matcher = ComponentMatcher(UniversVersionMatcher())
    store = FileAdvisoryStore(settings.okf_root)
    job = partial(run_ingest_job, uow_factory, registry, matcher, store, _now)
    return create_app(
        uow_factory,
        enable_docs=settings.enable_docs,
        ingest_runner=ThreadIngestRunner(job, _now),
        source_registry=registry,
        on_startup=partial(reset_interrupted_runs, uow_factory),
    )


app = build_app()
