"""Composition Root: der einzige Ort, der alle Schichten kennt und verdrahtet."""

from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial

import httpx
from fastapi import FastAPI

from app.application.component_matching import ComponentMatcher
from app.application.github_sync import GitHubSyncServices, SyncRequest, run_github_sync
from app.application.ingest import run_ingest_job, run_scan_then_sync
from app.application.ingest_runner import IngestRunner
from app.application.scan_runs import reset_interrupted_runs, run_recorded_scan
from app.application.scan_schedule import parse_scan_schedule, start_catch_up_if_due
from app.application.source_registry import SourceRegistry
from app.application.unit_of_work import UnitOfWorkFactory
from app.infrastructure.config import Settings, get_settings
from app.infrastructure.database import create_session_factory
from app.infrastructure.github.app_client import GitHubAppIssueTracker
from app.infrastructure.job_gate import JobGate
from app.infrastructure.okf_store import FileAdvisoryStore
from app.infrastructure.sbom.cyclonedx import CycloneDxParser
from app.infrastructure.scan_scheduler import ApsScanScheduler
from app.infrastructure.sources.catalog import build_sources
from app.infrastructure.sources.http_cache import HttpCache
from app.infrastructure.thread_ingest_runner import ThreadIngestRunner
from app.infrastructure.thread_sync_runner import ThreadSyncRunner
from app.infrastructure.unit_of_work import sqlalchemy_unit_of_work
from app.infrastructure.univers_matcher import UniversVersionMatcher
from app.presentation.app_factory import AppServices, create_app
from app.presentation.issue_export_markdown import MarkdownIssueFormatter

_HTTP_TIMEOUT_SECONDS = 60.0


def _now() -> datetime:
    return datetime.now(UTC)


def _lifecycle(
    settings: Settings, uow_factory: UnitOfWorkFactory, runner: IngestRunner
) -> tuple[Callable[[], None], Callable[[], None] | None]:
    """Start: aufräumen, ggf. nachholen, Zeitplan starten. Ohne Zeitplan nur aufräumen."""
    reset = partial(reset_interrupted_runs, uow_factory, _now)
    if not settings.scan_schedule_enabled:
        return reset, None
    schedule = parse_scan_schedule(settings.scan_schedule_time, settings.scan_schedule_timezone)
    scheduler = ApsScanScheduler(runner, schedule)

    def startup() -> None:
        reset()
        start_catch_up_if_due(uow_factory, _now, runner)
        scheduler.start()

    return startup, scheduler.shutdown


def build_app() -> FastAPI:
    settings = get_settings()
    uow_factory = partial(
        sqlalchemy_unit_of_work, create_session_factory(settings.sqlalchemy_url())
    )
    client = httpx.Client(timeout=_HTTP_TIMEOUT_SECONDS, headers={"User-Agent": "cve-radar"})
    versions = UniversVersionMatcher()
    cache = HttpCache(settings.source_cache_root, client)
    registry = SourceRegistry(build_sources(client, cache, versions, settings.osv_base_url))
    matcher = ComponentMatcher(versions)
    store = FileAdvisoryStore(settings.okf_root)
    gate = JobGate()
    tracker = GitHubAppIssueTracker(settings)
    github = GitHubSyncServices(tracker, MarkdownIssueFormatter(), store, _now)
    sync_job = partial(run_github_sync, uow_factory, github)
    scan = partial(run_ingest_job, uow_factory, registry, matcher, store, _now)
    automatic_sync = partial(sync_job, SyncRequest(None, create_issues=False, min_level=None))
    job = partial(
        run_recorded_scan, uow_factory, _now, partial(run_scan_then_sync, scan, automatic_sync)
    )
    runner = ThreadIngestRunner(job, _now, gate)
    on_startup, on_shutdown = _lifecycle(settings, uow_factory, runner)
    return create_app(
        uow_factory,
        enable_docs=settings.enable_docs,
        services=AppServices(
            ingest_runner=runner,
            advisory_store=store,
            source_registry=registry,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            sbom_parser=CycloneDxParser(),
            clock=_now,
            github_tracker=tracker,
            github_sync_runner=ThreadSyncRunner(sync_job, _now, gate),
        ),
    )


app = build_app()
