"""Use Cases rund um die Aufzeichnung von Scan-Läufen."""

from collections.abc import Callable
from dataclasses import dataclass

from app.application.ingest import Clock, IngestResult
from app.application.source_use_cases import ResetInterruptedRuns
from app.application.unit_of_work import UnitOfWork, UnitOfWorkFactory
from app.domain.scan_run import ScanCounts, ScanOutcome, ScanRun, ScanTrigger


def outcome_of(result: IngestResult) -> tuple[ScanOutcome, int, str]:
    """Ergebnis, Anzahl der Quellen mit Lücken und eine kurze Meldung."""
    unreliable = [source.source_key for source in result.sources if source.unreliable]
    if not unreliable:
        return ScanOutcome.OK, 0, ""
    message = f"{len(unreliable)} Quellen mit Fehlern: {', '.join(unreliable)}"
    return ScanOutcome.INCOMPLETE, len(unreliable), message


def _start(uow_factory: UnitOfWorkFactory, clock: Clock, trigger: ScanTrigger) -> ScanRun:
    with uow_factory() as uow:
        run = uow.scan_runs.add(ScanRun(trigger=trigger, started_at=clock()))
        uow.commit()
        return run


def _save(uow_factory: UnitOfWorkFactory, run: ScanRun) -> None:
    with uow_factory() as uow:
        uow.scan_runs.update(run)
        uow.commit()


def _finished(run: ScanRun, result: IngestResult, clock: Clock) -> ScanRun:
    outcome, sources_with_errors, message = outcome_of(result)
    counts = ScanCounts(
        components_scanned=result.components_scanned,
        findings_found=result.findings_found,
        sources_with_errors=sources_with_errors,
    )
    return run.finish(outcome, clock(), counts=counts, message=message)


def run_recorded_scan(
    uow_factory: UnitOfWorkFactory,
    clock: Clock,
    scan: Callable[[], IngestResult],
    trigger: ScanTrigger,
) -> IngestResult:
    """Führt den Scan aus und hält Beginn und Ergebnis in eigenen Transaktionen fest."""
    run = _start(uow_factory, clock, trigger)
    try:
        result = scan()
    except Exception as error:
        failure = f"Lauf fehlgeschlagen ({type(error).__name__})"
        _save(uow_factory, run.finish(ScanOutcome.FAILED, clock(), message=failure))
        raise
    _save(uow_factory, _finished(run, result, clock))
    return result


class ResetInterruptedScans:
    """Beim Start: Läufe ohne Ende hat ein Neustart abgebrochen."""

    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    def execute(self) -> int:
        unfinished = self._uow.scan_runs.list_unfinished()
        for run in unfinished:
            self._uow.scan_runs.update(run.interrupt(self._clock()))
        self._uow.commit()
        return len(unfinished)


@dataclass(frozen=True)
class ScanHistory:
    last_run: ScanRun | None
    last_usable_run: ScanRun | None


class GetScanHistory:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self) -> ScanHistory:
        return ScanHistory(
            last_run=self._uow.scan_runs.latest_finished(),
            last_usable_run=self._uow.scan_runs.latest_usable(),
        )


def reset_interrupted_runs(uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
    """Beim Start: Quellen und Scan-Läufe aufräumen, die ein Neustart unterbrochen hat."""
    with uow_factory() as uow:
        ResetInterruptedRuns(uow).execute()
        ResetInterruptedScans(uow, clock).execute()
