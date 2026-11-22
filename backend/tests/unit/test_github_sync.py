from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.application.github_sync import SyncGitHubIssues, SyncRequest
from app.application.issue_export import ExportApplicationIssues
from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.vulnerability import (
    Advisory,
    Finding,
    FindingStatus,
    IssueState,
    ResolutionSource,
    RiskScore,
    Severity,
)
from tests.fakes import FakeAdvisoryStore, FakeIssueFormatter, FakeIssueTracker, InMemoryUnitOfWork

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)
_RISK_VALUES = {
    Severity.KRITISCH: 98,
    Severity.HOCH: 80,
    Severity.MITTEL: 50,
    Severity.NIEDRIG: 20,
}
REPO = "acme/shop"
ISSUE_7 = "https://github.com/acme/shop/issues/7"


@dataclass(frozen=True)
class FindingSpec:
    status: FindingStatus = FindingStatus.OPEN
    level: Severity = Severity.HOCH
    issue_url: str = ""
    issue_state: IssueState | None = None
    first_seen_at: datetime | None = None
    resolved_by: ResolutionSource | None = None
    resolution: str = ""
    application_id: int | None = None


class World:
    def __init__(self) -> None:
        self.uow = InMemoryUnitOfWork()
        self.tracker = FakeIssueTracker()
        self.app_id = self.application(repository=REPO)

    def application(
        self,
        name: str = "Shop",
        *,
        repository: str | None = None,
        min_level: Severity | None = None,
        enabled_at: datetime | None = None,
    ) -> int:
        app = self.uow.applications.add(
            Application(
                name=name,
                github_repository=repository,
                auto_issue_min_level=min_level,
                auto_issue_enabled_at=enabled_at,
            )
        )
        assert app.id is not None
        return app.id

    def component(self, application_id: int, name: str, *, retired: bool = False) -> int:
        component = self.uow.components.add(
            application_id,
            Component(
                name,
                "1.0",
                Category.LIBRARY,
                Ecosystem.NPM,
                True,
                retired_in_version_id=99 if retired else None,
            ),
        )
        assert component.id is not None
        return component.id

    def advisory(self, advisory_id: str) -> None:
        self.uow.advisories.upsert(
            Advisory(
                advisory_id=advisory_id,
                cve_id=advisory_id,
                title=f"Titel {advisory_id}",
                description="d",
                cvss_base=7.5,
                fixed_version="1.0.1",
                references=[],
                okf_path="",
            )
        )

    def finding(
        self, advisory_id: str, component_id: int, spec: FindingSpec | None = None
    ) -> Finding:
        options = spec or FindingSpec()
        self.advisory(advisory_id)
        return self.uow.findings.upsert(
            Finding(
                advisory_id=advisory_id,
                component_id=component_id,
                application_id=options.application_id or self.app_id,
                found_version="1.0",
                risk=RiskScore(
                    value=_RISK_VALUES[options.level], level=options.level, rationale="r"
                ),
                status=options.status,
                issue_url=options.issue_url,
                issue_state=options.issue_state,
                first_seen_at=options.first_seen_at or NOW,
                resolved_by=options.resolved_by,
                resolution=options.resolution,
                resolved_at=NOW if options.resolved_by else None,
            )
        )

    def sync(self, request: SyncRequest) -> list[str]:
        use_case = SyncGitHubIssues(
            self.uow,
            self.tracker,
            FakeIssueFormatter(),
            ExportApplicationIssues(self.uow, FakeAdvisoryStore(), lambda: NOW),
            lambda: NOW,
        )
        return [outcome.message for outcome in use_case.execute(request)]

    def sync_links(self) -> list[str]:
        return self.sync(SyncRequest(None, create_issues=False, min_level=None))

    def stored(self, finding: Finding) -> Finding:
        return next(item for item in self.uow.findings.list() if item.id == finding.id)


def test_button_creates_issues_from_threshold_in_risk_order() -> None:
    world = World()
    component = world.component(world.app_id, "react")
    high = world.finding("CVE-1", component, FindingSpec(level=Severity.HOCH))
    world.finding("CVE-2", component, FindingSpec(level=Severity.NIEDRIG))
    critical = world.finding("CVE-3", component, FindingSpec(level=Severity.KRITISCH))

    messages = world.sync(SyncRequest(world.app_id, create_issues=True, min_level=Severity.HOCH))

    assert [content.marker for _, content in world.tracker.created] == [
        f"<!-- cve-radar:application={world.app_id};advisory=CVE-3 -->",
        f"<!-- cve-radar:application={world.app_id};advisory=CVE-1 -->",
    ]
    assert world.stored(critical).issue_url.endswith("/issues/1")
    assert world.stored(high).issue_state == IssueState.OPEN
    assert messages == ["2 angelegt"]


def test_existing_marker_is_linked_instead_of_created_as_duplicate() -> None:
    world = World()
    component = world.component(world.app_id, "react")
    finding = world.finding("CVE-1", component)
    world.tracker.add_issue(REPO, 5, is_open=True)
    marker = f"<!-- cve-radar:application={world.app_id};advisory=CVE-1 -->"
    world.tracker.markers[REPO] = {marker: world.tracker.issues[(REPO, 5)]}

    messages = world.sync(SyncRequest(world.app_id, create_issues=True, min_level=Severity.NIEDRIG))

    assert world.tracker.created == []
    assert world.stored(finding).issue_url == "https://github.com/acme/shop/issues/5"
    assert messages == ["1 verknüpft"]


def test_findings_with_issue_link_are_not_created_again() -> None:
    world = World()
    component = world.component(world.app_id, "react")
    world.finding("CVE-1", component, FindingSpec(issue_url=ISSUE_7, issue_state=IssueState.OPEN))
    world.tracker.add_issue(REPO, 7, is_open=True)

    world.sync(SyncRequest(world.app_id, create_issues=True, min_level=Severity.NIEDRIG))

    assert world.tracker.created == []


def test_automatic_creation_only_for_findings_seen_after_enable() -> None:
    world = World()
    enabled = NOW - timedelta(days=1)
    app = world.uow.applications.get(world.app_id)
    app.auto_issue_min_level = Severity.HOCH
    app.auto_issue_enabled_at = enabled
    component = world.component(world.app_id, "react")
    world.finding("CVE-OLD", component, FindingSpec(first_seen_at=enabled - timedelta(days=5)))
    world.finding("CVE-NEW", component, FindingSpec(first_seen_at=NOW))

    world.sync_links()

    created = [content.marker for _, content in world.tracker.created]
    assert created == [f"<!-- cve-radar:application={world.app_id};advisory=CVE-NEW -->"]


def test_closed_issue_completed_marks_open_findings_fixed() -> None:
    world = World()
    component = world.component(world.app_id, "react")
    finding = world.finding(
        "CVE-1", component, FindingSpec(issue_url=ISSUE_7, issue_state=IssueState.OPEN)
    )
    world.tracker.add_issue(REPO, 7, is_open=False)

    messages = world.sync_links()

    stored = world.stored(finding)
    assert stored.status == FindingStatus.FIXED
    assert stored.resolved_by == ResolutionSource.REPORTED
    assert stored.resolution == "Issue #7 geschlossen"
    assert stored.issue_state == IssueState.CLOSED
    assert messages == ["1 geschlossen"]


def test_closed_issue_not_planned_marks_open_findings_accepted() -> None:
    world = World()
    component = world.component(world.app_id, "react")
    finding = world.finding(
        "CVE-1", component, FindingSpec(issue_url=ISSUE_7, issue_state=IssueState.OPEN)
    )
    world.tracker.add_issue(REPO, 7, is_open=False, not_planned=True)

    world.sync_links()

    stored = world.stored(finding)
    assert stored.status == FindingStatus.ACCEPTED
    assert "Issue #7 als not planned geschlossen" in stored.comment


def test_reopened_issue_reopens_fixed_findings_with_note() -> None:
    world = World()
    component = world.component(world.app_id, "react")
    finding = world.finding(
        "CVE-1",
        component,
        FindingSpec(
            status=FindingStatus.FIXED,
            issue_url=ISSUE_7,
            issue_state=IssueState.CLOSED,
            resolved_by=ResolutionSource.REPORTED,
            resolution="Issue #7 geschlossen",
        ),
    )
    world.tracker.add_issue(REPO, 7, is_open=True)

    world.sync_links()

    stored = world.stored(finding)
    assert stored.status == FindingStatus.OPEN
    assert stored.resolved_by is None
    assert "Issue #7 wieder geöffnet" in stored.comment
    assert stored.issue_state == IssueState.OPEN


def test_user_rating_closes_issue_as_not_planned() -> None:
    world = World()
    component = world.component(world.app_id, "react")
    world.finding(
        "CVE-1",
        component,
        FindingSpec(status=FindingStatus.ACCEPTED, issue_url=ISSUE_7, issue_state=IssueState.OPEN),
    )
    world.tracker.add_issue(REPO, 7, is_open=True)

    world.sync_links()

    assert world.tracker.set_open_calls == [
        (REPO, 7, False, "In CVE-Radar als akzeptiert bewertet", True)
    ]


def test_sbom_fix_closes_issue_as_completed_with_resolution() -> None:
    world = World()
    component = world.component(world.app_id, "react")
    world.finding(
        "CVE-1",
        component,
        FindingSpec(
            status=FindingStatus.FIXED,
            issue_url=ISSUE_7,
            issue_state=IssueState.OPEN,
            resolved_by=ResolutionSource.SBOM,
            resolution="Komponente ausgebaut",
        ),
    )
    world.tracker.add_issue(REPO, 7, is_open=True)

    world.sync_links()

    assert world.tracker.set_open_calls == [
        (REPO, 7, False, "Behoben: Komponente ausgebaut", False)
    ]


def test_missing_issue_is_reported_and_left_alone() -> None:
    world = World()
    component = world.component(world.app_id, "react")
    finding = world.finding(
        "CVE-1", component, FindingSpec(issue_url=ISSUE_7, issue_state=IssueState.OPEN)
    )

    messages = world.sync_links()

    assert world.stored(finding).status == FindingStatus.OPEN
    assert messages == ["Issue #7 nicht gefunden"]


def test_error_in_one_application_does_not_stop_the_others() -> None:
    world = World()
    other_id = world.application("Api", repository="acme/api")
    world.tracker.failing_repos.add(REPO)
    world.finding("CVE-8", world.component(world.app_id, "react"))
    component = world.component(other_id, "flask")
    world.finding("CVE-9", component, FindingSpec(application_id=other_id))

    messages = world.sync(SyncRequest(None, create_issues=True, min_level=Severity.NIEDRIG))

    assert messages == ["GitHub ist nicht erreichbar", "1 angelegt"]
    assert world.uow.applications.get(world.app_id).github_sync_message == (
        "GitHub ist nicht erreichbar"
    )
    assert world.uow.rollbacks == 1
