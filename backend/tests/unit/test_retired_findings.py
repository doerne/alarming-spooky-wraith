from dataclasses import replace
from datetime import UTC, datetime

from app.application.retired_findings import ResolveRetiredFindings
from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.ports import AdvisoryDocument, SourceReference
from app.domain.sbom import Sbom, SbomVersion
from app.domain.vulnerability import (
    Advisory,
    Finding,
    FindingStatus,
    ResolutionSource,
    RiskScore,
    Severity,
)
from tests.fakes import FakeAdvisoryStore, InMemoryUnitOfWork

_NOW = datetime(2026, 11, 22, 3, 0, tzinfo=UTC)


class _World:
    def __init__(self) -> None:
        self.uow = InMemoryUnitOfWork()
        application = self.uow.applications.add(Application(name="Shop"))
        assert application.id is not None
        self.application_id = application.id
        sbom = self.uow.sboms.add(Sbom(application_id=application.id, name="backend-image"))
        assert sbom.id is not None
        self.sbom_id = sbom.id
        self.uow.advisories.upsert(Advisory("CVE-1", "CVE-1", "t", "d", 7.5, "3.1.6", [], ""))
        self.store = FakeAdvisoryStore()
        self.store.documents["CVE-1"] = AdvisoryDocument(
            "d", "", [], [SourceReference("osv", "https://osv.dev/CVE-1")]
        )

    def version(self, label: str) -> int:
        version = self.uow.sbom_versions.add(SbomVersion(self.sbom_id, label, _NOW, None, True, ()))
        assert version.id is not None
        return version.id

    def component(self, version: str, *, retired_in: int | None = None) -> Component:
        component = Component(
            "jinja2", version, Category.LIBRARY, Ecosystem.PYPI, True, sbom_id=self.sbom_id
        )
        return self.uow.components.add(
            self.application_id, replace(component, retired_in_version_id=retired_in)
        )

    def finding(
        self, component: Component, status: FindingStatus = FindingStatus.OPEN, comment: str = ""
    ) -> None:
        assert component.id is not None
        self.uow.findings.upsert(
            Finding(
                advisory_id="CVE-1",
                component_id=component.id,
                application_id=self.application_id,
                found_version=component.version,
                risk=RiskScore(value=75, level=Severity.HOCH, rationale=""),
                status=status,
                comment=comment,
            )
        )

    def resolve(self, failed: frozenset[str] = frozenset()) -> int:
        return ResolveRetiredFindings(self.uow, self.store, lambda: _NOW).execute(failed)


def test_resolves_to_fixed_when_cve_gone() -> None:
    world = _World()
    old = world.component("3.1.4", retired_in=world.version("v1.5.0"))
    world.finding(old, FindingStatus.IN_PROGRESS, "PR #3")
    assert world.resolve() == 1
    [finding] = world.uow.findings.list()
    assert finding.status == FindingStatus.FIXED
    assert finding.resolved_at == _NOW
    assert finding.resolution == "Komponente ausgebaut mit SBOM backend-image v1.5.0"
    assert finding.resolved_by == ResolutionSource.SBOM
    assert finding.comment == "PR #3"


def test_keeps_false_positive() -> None:
    world = _World()
    old = world.component("3.1.4", retired_in=world.version("v1.5.0"))
    world.finding(old, FindingStatus.FALSE_POSITIVE)
    world.resolve()
    [finding] = world.uow.findings.list()
    assert finding.status == FindingStatus.FALSE_POSITIVE
    assert finding.resolved_at == _NOW


def test_transfers_triage_to_successor() -> None:
    world = _World()
    old = world.component("3.1.4", retired_in=world.version("v1.5.0"))
    world.finding(old, FindingStatus.IN_PROGRESS, "PR #3")
    successor = world.component("3.1.5")
    world.finding(successor)
    assert world.resolve() == 0
    [finding] = world.uow.findings.list()
    assert finding.component_id == successor.id
    assert (finding.status, finding.comment) == (FindingStatus.IN_PROGRESS, "PR #3")
    assert finding.resolved_at is None


def test_successor_keeps_its_own_status_when_already_triaged() -> None:
    world = _World()
    old = world.component("3.1.4", retired_in=world.version("v1.5.0"))
    world.finding(old, FindingStatus.IN_PROGRESS, "alt")
    successor = world.component("3.1.5")
    world.finding(successor, FindingStatus.ACCEPTED, "neu")
    world.resolve()
    [finding] = world.uow.findings.list()
    assert (finding.status, finding.comment) == (FindingStatus.ACCEPTED, "neu\n\nalt")


def test_cleans_up_retired_component_without_findings() -> None:
    world = _World()
    old = world.component("3.1.4", retired_in=world.version("v1.5.0"))
    world.finding(old)
    world.finding(world.component("3.1.5"))
    world.resolve()
    assert old.id is not None
    assert [c.version for c in world.uow.components.list_for_application(world.application_id)] == [
        "3.1.5"
    ]


def test_mentions_retiring_version_and_skips_resolved() -> None:
    world = _World()
    first = world.component("3.1.3", retired_in=world.version("v1.4.0"))
    world.finding(first)
    world.resolve()
    second = world.component("3.1.4", retired_in=world.version("v1.5.0"))
    world.finding(second)
    assert world.resolve() == 1
    resolutions = sorted(finding.resolution for finding in world.uow.findings.list())
    assert resolutions == [
        "Komponente ausgebaut mit SBOM backend-image v1.4.0",
        "Komponente ausgebaut mit SBOM backend-image v1.5.0",
    ]


def test_waits_when_reporting_source_failed() -> None:
    world = _World()
    old = world.component("3.1.4", retired_in=world.version("v1.5.0"))
    world.finding(old)
    assert world.resolve(frozenset({"osv"})) == 0
    assert world.uow.findings.list()[0].status == FindingStatus.OPEN
    assert world.uow.components.get(old.id or 0).is_retired


def test_resolves_when_only_unrelated_source_failed() -> None:
    world = _World()
    old = world.component("3.1.4", retired_in=world.version("v1.5.0"))
    world.finding(old)
    assert world.resolve(frozenset({"ghsa", "symfony"})) == 1


def test_waits_on_any_failure_without_known_origin() -> None:
    world = _World()
    del world.store.documents["CVE-1"]
    old = world.component("3.1.4", retired_in=world.version("v1.5.0"))
    world.finding(old)
    assert world.resolve(frozenset({"ghsa"})) == 0
    assert world.resolve() == 1
