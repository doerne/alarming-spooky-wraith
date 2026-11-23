from dataclasses import replace
from datetime import UTC, datetime, timedelta

from app.application.applications_overview import GetApplicationsOverview
from app.domain.application_overview import ApplicationOverview, ScanState
from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.sbom import Sbom, SbomVersion
from app.domain.scan_run import ScanCounts, ScanOutcome, ScanRun, ScanTrigger
from app.domain.vulnerability import Finding, FindingStatus, RiskScore, Severity
from tests.fakes import InMemoryUnitOfWork

_NOW = datetime(2026, 12, 10, 10, 0, tzinfo=UTC)


def _application(
    uow: InMemoryUnitOfWork,
    name: str,
    github_repository: str | None = None,
    inventory_changed_at: datetime | None = None,
) -> int:
    application = uow.applications.add(
        Application(
            name=name,
            github_repository=github_repository,
            inventory_changed_at=inventory_changed_at,
        )
    )
    assert application.id is not None
    return application.id


def _component(uow: InMemoryUnitOfWork, application_id: int, name: str = "react") -> int:
    component = uow.components.add(
        application_id,
        Component(
            name=name,
            version="1.0.0",
            category=Category.LIBRARY,
            ecosystem=Ecosystem.NPM,
            direct=True,
        ),
    )
    assert component.id is not None
    return component.id


def _finding(
    uow: InMemoryUnitOfWork,
    ids: tuple[int, int],
    advisory_id: str,
    level: Severity,
    status: FindingStatus = FindingStatus.OPEN,
) -> None:
    application_id, component_id = ids
    uow.findings.upsert(
        Finding(
            advisory_id=advisory_id,
            component_id=component_id,
            application_id=application_id,
            found_version="1.0.0",
            risk=RiskScore(value=90, level=level, rationale="r"),
            status=status,
            first_seen_at=datetime(2026, 11, 23, tzinfo=UTC),
        )
    )


def _overview(uow: InMemoryUnitOfWork) -> dict[str, ApplicationOverview]:
    rows = GetApplicationsOverview(uow, lambda: _NOW).execute()
    return {row.name: row for row in rows}


def _usable_scan(uow: InMemoryUnitOfWork, started: datetime) -> None:
    run = uow.scan_runs.add(ScanRun(trigger=ScanTrigger.SCHEDULE, started_at=started))
    counts = ScanCounts(components_scanned=1, findings_found=0, sources_with_errors=0)
    uow.scan_runs.update(run.finish(ScanOutcome.OK, started, counts=counts, message=""))


def test_counts_open_findings_by_severity_and_overdue() -> None:
    uow = InMemoryUnitOfWork()
    shop = _application(uow, "Shop")
    ids = (shop, _component(uow, shop))
    _finding(uow, ids, "CVE-1", Severity.KRITISCH)
    _finding(uow, ids, "CVE-2", Severity.HOCH)
    _finding(uow, ids, "CVE-3", Severity.KRITISCH, FindingStatus.FIXED)

    row = _overview(uow)["Shop"]

    assert row.open_by_severity == {
        Severity.KRITISCH: 1,
        Severity.HOCH: 1,
        Severity.MITTEL: 0,
        Severity.NIEDRIG: 0,
    }
    assert row.overdue == 1


def test_retired_component_counts_finding_but_not_component() -> None:
    uow = InMemoryUnitOfWork()
    shop = _application(uow, "Shop")
    _component(uow, shop, "active")
    retired_id = _component(uow, shop, "retired")
    uow.components.update(replace(uow.components.get(retired_id), retired_in_version_id=1))
    _finding(uow, (shop, retired_id), "CVE-1", Severity.MITTEL)

    row = _overview(uow)["Shop"]

    assert row.component_count == 1
    assert row.open_by_severity[Severity.MITTEL] == 1


def test_application_without_data() -> None:
    uow = InMemoryUnitOfWork()
    _application(uow, "Leer")

    row = _overview(uow)["Leer"]

    assert sum(row.open_by_severity.values()) == 0
    assert row.overdue == 0
    assert row.component_count == 0
    assert row.latest_sbom_upload_at is None
    assert row.sbom_stale is True
    assert row.scan_state == ScanState.NEVER_SCANNED
    assert row.github_repository is None


def test_scan_state_uses_last_usable_run() -> None:
    uow = InMemoryUnitOfWork()
    _usable_scan(uow, datetime(2026, 12, 10, 4, 0, tzinfo=UTC))
    _application(uow, "Geändert", inventory_changed_at=datetime(2026, 12, 10, 9, 0, tzinfo=UTC))
    _application(uow, "Unverändert")

    rows = _overview(uow)

    assert rows["Geändert"].scan_state == ScanState.CHANGED_SINCE_SCAN
    assert rows["Unverändert"].scan_state == ScanState.CURRENT


def test_other_applications_are_separate() -> None:
    uow = InMemoryUnitOfWork()
    shop = _application(uow, "Shop", github_repository="acme/shop")
    _application(uow, "Blog")
    _finding(uow, (shop, _component(uow, shop)), "CVE-1", Severity.NIEDRIG)
    sbom = uow.sboms.add(Sbom(application_id=shop, name="backend"))
    assert sbom.id is not None
    uploaded = _NOW - timedelta(days=2)
    uow.sbom_versions.add(SbomVersion(sbom.id, "v1", uploaded, None, True, ()))

    rows = _overview(uow)

    assert rows["Shop"].latest_sbom_upload_at == uploaded
    assert rows["Shop"].sbom_stale is False
    assert rows["Shop"].github_repository == "acme/shop"
    assert sum(rows["Blog"].open_by_severity.values()) == 0
    assert rows["Blog"].latest_sbom_upload_at is None
    assert list(rows) == ["Blog", "Shop"]
