from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.application.issue_export import ExportApplicationIssues, IssueExport
from app.domain.errors import EntityNotFoundError
from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.ports import AdvisoryDocument
from app.domain.sbom import Sbom
from app.domain.vulnerability import Advisory, Finding, FindingStatus, RiskScore, Severity
from tests.fakes import FakeAdvisoryStore, InMemoryUnitOfWork

_NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


class _World:
    def __init__(self) -> None:
        self.uow = InMemoryUnitOfWork()
        self.store = FakeAdvisoryStore()
        self.application_id = self.application("Shop")

    def application(self, name: str) -> int:
        application = self.uow.applications.add(Application(name=name))
        assert application.id is not None
        return application.id

    def component(
        self, name: str, *, application_id: int | None = None, sbom_id: int | None = None
    ) -> Component:
        return self.uow.components.add(
            application_id or self.application_id,
            Component(name, "1.0.0", Category.LIBRARY, Ecosystem.NPM, True, sbom_id=sbom_id),
        )

    def advisory(
        self,
        advisory_id: str,
        *,
        without_cve: bool = False,
        description: str = "",
        cvss_base: float | None = 7.5,
        references: list[str] | None = None,
    ) -> None:
        self.uow.advisories.upsert(
            Advisory(
                advisory_id=advisory_id,
                cve_id=None if without_cve else advisory_id,
                title=f"Titel {advisory_id}",
                description=description or f"DB-Beschreibung {advisory_id}",
                cvss_base=cvss_base,
                fixed_version="1.0.1",
                references=references or [f"https://example.org/{advisory_id}"],
                okf_path="",
            )
        )

    def finding(
        self,
        advisory_id: str,
        component: Component,
        score: int,
        status: FindingStatus = FindingStatus.OPEN,
        comment: str = "",
    ) -> None:
        assert component.id is not None
        assert component.application_id is not None
        self.uow.findings.upsert(
            Finding(
                advisory_id=advisory_id,
                component_id=component.id,
                application_id=component.application_id,
                found_version=component.version,
                risk=RiskScore(value=score, level=Severity.HOCH, rationale=""),
                status=status,
                comment=comment,
            )
        )

    def export(self, application_id: int | None = None) -> IssueExport:
        use_case = ExportApplicationIssues(self.uow, self.store, lambda: _NOW)
        return use_case.execute(application_id or self.application_id)


def test_exports_only_open_and_in_progress_findings() -> None:
    world = _World()
    for advisory_id, status in [
        ("CVE-1", FindingStatus.OPEN),
        ("CVE-2", FindingStatus.IN_PROGRESS),
        ("CVE-3", FindingStatus.FIXED),
    ]:
        world.advisory(advisory_id)
        world.finding(advisory_id, world.component(f"pkg-{advisory_id}"), 50, status)
    export = world.export()
    assert sorted(issue.advisory_id for issue in export.issues) == ["CVE-1", "CVE-2"]
    assert export.application_name == "Shop"
    assert export.generated_at == _NOW


def test_groups_components_per_advisory_with_highest_risk() -> None:
    world = _World()
    sbom = world.uow.sboms.add(Sbom(application_id=world.application_id, name="backend-image"))
    world.advisory("CVE-1")
    world.finding("CVE-1", world.component("react"), 50)
    world.finding("CVE-1", world.component("react", sbom_id=sbom.id), 90)
    [issue] = world.export().issues
    assert issue.risk_score == 90
    assert [c.source for c in issue.components] == ["backend-image", "manuell"]


def test_sorts_by_score_then_advisory_id() -> None:
    world = _World()
    for advisory_id, score in [("CVE-B", 40), ("CVE-A", 40), ("CVE-C", 95)]:
        world.advisory(advisory_id)
        world.finding(advisory_id, world.component(advisory_id.lower()), score)
    assert [issue.advisory_id for issue in world.export().issues] == ["CVE-C", "CVE-A", "CVE-B"]


def test_ignores_findings_of_other_applications() -> None:
    world = _World()
    other = world.application("Andere")
    world.advisory("CVE-1")
    world.finding("CVE-1", world.component("react"), 50)
    world.finding("CVE-1", world.component("vue", application_id=other), 99)
    [issue] = world.export().issues
    assert issue.risk_score == 50
    assert [c.name for c in issue.components] == ["react"]


def test_falls_back_without_document() -> None:
    world = _World()
    world.advisory("GHSA-xxxx", without_cve=True, cvss_base=9.8)
    world.finding("GHSA-xxxx", world.component("react"), 98)
    [issue] = world.export().issues
    assert issue.cve_id is None
    assert issue.description == "DB-Beschreibung GHSA-xxxx"
    assert issue.rationale != ""
    assert issue.references == ("https://example.org/GHSA-xxxx",)


def test_uses_document_description_rationale_and_references() -> None:
    world = _World()
    world.advisory("CVE-1")
    world.store.documents["CVE-1"] = AdvisoryDocument(
        "Datei-Beschreibung", "CVSS 7.5 → hoch", ["https://a", "https://b"], []
    )
    world.finding("CVE-1", world.component("react"), 75)
    [issue] = world.export().issues
    assert (issue.description, issue.rationale, issue.references) == (
        "Datei-Beschreibung",
        "CVSS 7.5 → hoch",
        ("https://a", "https://b"),
    )


def test_truncates_description_and_references() -> None:
    world = _World()
    references = [f"https://example.org/{index}" for index in range(12)]
    world.advisory("CVE-1", description="x" * 5_000, references=references)
    world.finding("CVE-1", world.component("react"), 50)
    [issue] = world.export().issues
    assert len(issue.description) == 4_001
    assert issue.description.endswith("…")
    assert len(issue.references) == 10


def test_keeps_triage_comment_per_component() -> None:
    world = _World()
    world.advisory("CVE-1")
    react = world.component("react")
    world.finding("CVE-1", react, 50, FindingStatus.IN_PROGRESS, comment="Upgrade in PR #12")
    [issue] = world.export().issues
    assert issue.components[0].comment == "Upgrade in PR #12"
    assert issue.components[0].status == FindingStatus.IN_PROGRESS


def test_unknown_application_raises() -> None:
    world = _World()
    with pytest.raises(EntityNotFoundError):
        world.export(999)


def test_empty_export_has_no_issues() -> None:
    assert _World().export().issues == ()


def test_skips_unchecked_components() -> None:
    world = _World()
    world.advisory("CVE-1")
    openssl = world.component("openssl")
    world.uow.components.update(replace(openssl, checked=False))
    world.finding("CVE-1", openssl, 80)
    assert world.export().issues == ()


def test_skips_findings_of_deleted_components() -> None:
    world = _World()
    world.advisory("CVE-1")
    react = world.component("react")
    world.finding("CVE-1", react, 80)
    assert react.id is not None
    world.uow.components.delete_many([react.id])
    assert world.export().issues == ()


def test_falls_back_when_document_fields_are_empty() -> None:
    world = _World()
    world.advisory("CVE-1", cvss_base=9.8)
    world.store.documents["CVE-1"] = AdvisoryDocument("", "", [], [])
    world.finding("CVE-1", world.component("react"), 98)
    [issue] = world.export().issues
    assert issue.description == "DB-Beschreibung CVE-1"
    assert issue.rationale != ""
    assert issue.references == ("https://example.org/CVE-1",)
