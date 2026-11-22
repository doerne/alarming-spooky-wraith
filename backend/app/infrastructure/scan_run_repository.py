"""SQLAlchemy-Repository für Scan-Läufe."""

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.domain.errors import EntityNotFoundError
from app.domain.scan_run import ScanOutcome, ScanRun, ScanTrigger
from app.infrastructure.models import ScanRunModel
from app.infrastructure.repositories import as_utc

_USABLE = (ScanOutcome.OK.value, ScanOutcome.INCOMPLETE.value)


def _to_scan_run(model: ScanRunModel) -> ScanRun:
    return ScanRun(
        id=model.id,
        trigger=ScanTrigger(model.trigger),
        started_at=as_utc(model.started_at),
        finished_at=as_utc(model.finished_at) if model.finished_at else None,
        outcome=ScanOutcome(model.outcome) if model.outcome else None,
        components_scanned=model.components_scanned,
        findings_found=model.findings_found,
        sources_with_errors=model.sources_with_errors,
        message=model.message,
        interrupted=model.interrupted,
    )


def _apply(model: ScanRunModel, run: ScanRun) -> None:
    model.trigger = run.trigger.value
    model.started_at = run.started_at
    model.finished_at = run.finished_at
    model.outcome = run.outcome.value if run.outcome else None
    model.components_scanned = run.components_scanned
    model.findings_found = run.findings_found
    model.sources_with_errors = run.sources_with_errors
    model.message = run.message
    model.interrupted = run.interrupted


def _newest_first(query: Select[ScanRunModel]) -> Select[ScanRunModel]:
    return query.order_by(ScanRunModel.started_at.desc(), ScanRunModel.id.desc()).limit(1)


_FINISHED = select(ScanRunModel).where(ScanRunModel.finished_at.is_not(None))


class SqlAlchemyScanRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, run: ScanRun) -> ScanRun:
        model = ScanRunModel()
        _apply(model, run)
        self._session.add(model)
        self._session.flush()
        return _to_scan_run(model)

    def update(self, run: ScanRun) -> ScanRun:
        model = self._session.get(ScanRunModel, run.id)
        if model is None:
            raise EntityNotFoundError("Scan-Lauf", str(run.id))
        _apply(model, run)
        self._session.flush()
        return _to_scan_run(model)

    def list_unfinished(self) -> list[ScanRun]:
        query = select(ScanRunModel).where(ScanRunModel.finished_at.is_(None))
        return [_to_scan_run(model) for model in self._session.scalars(query)]

    def latest_finished(self) -> ScanRun | None:
        return self._first(_FINISHED)

    def latest_usable(self) -> ScanRun | None:
        return self._first(_FINISHED.where(ScanRunModel.outcome.in_(_USABLE)))

    def latest_regular_finished(self) -> ScanRun | None:
        return self._first(_FINISHED.where(ScanRunModel.interrupted.is_(False)))

    def latest_started(self, trigger: ScanTrigger) -> ScanRun | None:
        return self._first(select(ScanRunModel).where(ScanRunModel.trigger == trigger.value))

    def _first(self, query: Select[ScanRunModel]) -> ScanRun | None:
        model = self._session.scalars(_newest_first(query)).first()
        return _to_scan_run(model) if model else None
