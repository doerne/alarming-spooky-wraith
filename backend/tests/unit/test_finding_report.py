from datetime import UTC, datetime

import pytest

from app.application.finding_report import ProgressReport, ReportFindingProgress
from app.domain.errors import EntityNotFoundError
from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.vulnerability import (
    Advisory,
    Finding,
    FindingResolution,
    FindingStatus,
    ResolutionSource,
    RiskScore,
    Severity,
)
from tests.fakes import InMemoryUnitOfWork

_NOW = datetime(2026, 11, 22, 9, 0, tzinfo=UTC)
_ISSUE = "https://github.com/acme/shop/issues/12"


class _World:
    def __init__(self) -> None:
        self.uow = InMemoryUnitOfWork()
        self.application_id = self.application("Shop")
        self.uow.advisories.upsert(Advisory("CVE-1", "CVE-1", "t", "d", 7.5, None, [], ""))

    def application(self, name: str) -> int:
        application = self.uow.applications.add(Application(name=name))
        assert application.id is not None
        return application.id

    def finding(self, name: str, application_id: int | None = None, comment: str = "") -> None:
        target_application_id = application_id or self.application_id
        component = self.uow.components.add(
            target_application_id, Component(name, "1.0", Category.LIBRARY, Ecosystem.NPM, True)
        )
        assert component.id is not None
        self.uow.findings.upsert(
            Finding(
                "CVE-1",
                component.id,
                target_application_id,
                "1.0",
                RiskScore(value=75, level=Severity.HOCH, rationale=""),
                comment=comment,
            )
        )

    def report(self, report: ProgressReport, advisory_id: str = "CVE-1") -> tuple[str, int]:
        return ReportFindingProgress(self.uow, lambda: _NOW).execute(
            application_id=self.application_id, advisory_id=advisory_id, report=report
        )


def test_sets_issue_url_and_appends_comment_on_all_findings_of_the_cve() -> None:
    world = _World()
    world.finding("react", comment="alt")
    world.finding("react-dom")
    assert world.report(ProgressReport(issue_url=_ISSUE, comment="Issue angelegt")) == ("CVE-1", 2)
    findings = world.uow.findings.list()
    assert {f.issue_url for f in findings} == {_ISSUE}
    assert sorted(f.comment for f in findings) == ["Issue angelegt", "alt\n\nIssue angelegt"]
    assert world.uow.commits == 1


def test_reported_fix_is_provisional_and_named() -> None:
    world = _World()
    world.finding("react")
    world.report(ProgressReport(issue_url=_ISSUE))
    world.report(ProgressReport(status=FindingStatus.FIXED))
    [finding] = world.uow.findings.list()
    assert finding.status == FindingStatus.FIXED
    assert finding.resolved_by == ResolutionSource.REPORTED
    assert finding.resolved_at == _NOW
    assert finding.resolution == f"Als behoben gemeldet (Issue {_ISSUE})"


def test_other_status_clears_resolution() -> None:
    world = _World()
    world.finding("react")
    world.report(ProgressReport(status=FindingStatus.FIXED))
    world.report(ProgressReport(status=FindingStatus.IN_PROGRESS))
    [finding] = world.uow.findings.list()
    assert (finding.status, finding.resolved_at, finding.resolved_by, finding.resolution) == (
        FindingStatus.IN_PROGRESS,
        None,
        None,
        "",
    )


def test_resolves_absorbed_advisory_id() -> None:
    world = _World()
    world.finding("react")
    world.uow.advisory_aliases.save("GHSA-old", "CVE-1")
    assert world.report(ProgressReport(status=FindingStatus.IN_PROGRESS), "GHSA-old") == (
        "CVE-1",
        1,
    )


def test_unknown_cve_or_application_is_not_found() -> None:
    world = _World()
    other = world.application("Andere")
    world.finding("react", application_id=other)
    with pytest.raises(EntityNotFoundError):
        world.report(ProgressReport(status=FindingStatus.FIXED))
    world.application_id = 999
    with pytest.raises(EntityNotFoundError):
        world.report(ProgressReport(status=FindingStatus.FIXED))
    assert world.uow.findings.list()[0].status == FindingStatus.OPEN


def test_repeated_fix_keeps_existing_resolution() -> None:
    world = _World()
    world.finding("react")
    finding = world.uow.findings.list()[0]
    assert finding.id is not None
    sbom_time = datetime(2026, 11, 20, tzinfo=UTC)
    world.uow.findings.resolve(
        finding.id,
        FindingResolution(
            FindingStatus.FIXED, sbom_time, "ausgebaut", ResolutionSource.SBOM, sbom_time
        ),
    )
    world.report(ProgressReport(status=FindingStatus.FIXED, issue_url=_ISSUE))
    [stored] = world.uow.findings.list()
    assert (stored.resolved_by, stored.resolved_at, stored.resolution) == (
        ResolutionSource.SBOM,
        sbom_time,
        "ausgebaut",
    )
    assert stored.issue_url == _ISSUE


def test_status_report_spares_history_of_retired_components() -> None:
    world = _World()
    world.finding("react")
    retired = world.uow.components.add(
        world.application_id,
        Component("react", "0.9", Category.LIBRARY, Ecosystem.NPM, True, retired_in_version_id=1),
    )
    assert retired.id is not None
    world.uow.findings.upsert(
        Finding(
            "CVE-1",
            retired.id,
            world.application_id,
            "0.9",
            RiskScore(value=75, level=Severity.HOCH, rationale=""),
        )
    )
    history = world.uow.findings.list()[1]
    assert history.id is not None
    sbom_time = datetime(2026, 11, 20, tzinfo=UTC)
    world.uow.findings.resolve(
        history.id,
        FindingResolution(
            FindingStatus.FIXED, sbom_time, "ausgebaut", ResolutionSource.SBOM, sbom_time
        ),
    )
    assert world.report(
        ProgressReport(status=FindingStatus.IN_PROGRESS, comment="X", issue_url=_ISSUE)
    ) == ("CVE-1", 2)
    stored = world.uow.findings.list()[1]
    assert (stored.status, stored.resolved_by, stored.comment) == (
        FindingStatus.FIXED,
        ResolutionSource.SBOM,
        "",
    )
    assert stored.issue_url == _ISSUE
