"""Composition Root: der einzige Ort, der alle Schichten kennt und verdrahtet."""

from functools import partial

from fastapi import FastAPI

from app.infrastructure.config import get_settings
from app.infrastructure.database import create_session_factory
from app.infrastructure.unit_of_work import sqlalchemy_unit_of_work
from app.presentation.app_factory import create_app


def build_app() -> FastAPI:
    settings = get_settings()
    session_factory = create_session_factory(settings.sqlalchemy_url())
    return create_app(
        partial(sqlalchemy_unit_of_work, session_factory),
        enable_docs=settings.enable_docs,
    )


app = build_app()
