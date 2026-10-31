"""Composition Root: der einzige Ort, der alle Schichten kennt und verdrahtet."""

from functools import partial

import httpx
from fastapi import FastAPI

from app.infrastructure.config import get_settings
from app.infrastructure.database import create_session_factory
from app.infrastructure.okf_store import FileAdvisoryStore
from app.infrastructure.osv_client import HttpxOsvClient
from app.infrastructure.unit_of_work import sqlalchemy_unit_of_work
from app.presentation.app_factory import create_app


def build_app() -> FastAPI:
    settings = get_settings()
    session_factory = create_session_factory(settings.sqlalchemy_url())
    osv_client = HttpxOsvClient(settings.osv_base_url, httpx.Client(timeout=30.0))
    advisory_store = FileAdvisoryStore(settings.okf_root)
    return create_app(
        partial(sqlalchemy_unit_of_work, session_factory),
        enable_docs=settings.enable_docs,
        osv_client=osv_client,
        advisory_store=advisory_store,
    )


app = build_app()
