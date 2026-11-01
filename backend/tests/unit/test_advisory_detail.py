from datetime import UTC, datetime

import pytest

from app.application.advisory_detail import GetAdvisoryDetail
from app.application.component_matching import ComponentMatcher
from app.application.ingest import RunIngest
from app.application.inventory_use_cases import AddComponent, CreateApplication
from app.application.source_registry import SourceRegistry
from app.domain.errors import EntityNotFoundError
from app.domain.inventory import Category, Component, Ecosystem
from app.domain.ports import AdvisoryDocument, SourceReference, SourceVuln
from app.domain.vulnerability import Severity
from app.infrastructure.univers_matcher import UniversVersionMatcher
from tests.fakes import FakeAdvisoryStore, FakePackageSource, InMemoryUnitOfWork, descriptor

_VULN = SourceVuln(
    source_key="osv",
    id="GHSA-x",
    aliases=["CVE-2024-1"],
    summary="XSS in react",
    details="d",
    cvss_base=9.8,
    fixed_version="18.2.1",
    references=[],
    url="https://osv.dev/vulnerability/GHSA-x",
)


def _react(version: str = "18.2.0") -> Component:
    return Component(
        name="react",
        version=version,
        category=Category.LIBRARY,
        ecosystem=Ecosystem.NPM,
        direct=True,
    )


def _ingested(*app_names: str) -> tuple[InMemoryUnitOfWork, FakeAdvisoryStore]:
    uow = InMemoryUnitOfWork()
    for name in app_names:
        application = CreateApplication(uow).execute(name=name)
        assert application.id is not None
        AddComponent(uow).execute(application_id=application.id, component=_react())
    store = FakeAdvisoryStore()
    registry = SourceRegistry([FakePackageSource(descriptor("osv"), {"react": [_VULN]})])
    matcher = ComponentMatcher(UniversVersionMatcher())
    RunIngest(uow, registry, matcher, store, lambda: datetime.now(UTC)).execute()
    return uow, store


def test_detail_combines_db_and_document() -> None:
    uow, store = _ingested("Shop")
    store.documents["CVE-2024-1"] = AdvisoryDocument(
        "Langtext", "CVSS 9.8 -> 98/100", ["https://ref"], [SourceReference("osv", "https://o")]
    )
    detail = GetAdvisoryDetail(uow, store).execute("CVE-2024-1")
    assert detail.advisory_id == "CVE-2024-1"
    assert detail.cve_id == "CVE-2024-1"
    assert detail.title == "XSS in react"
    assert detail.cvss_base == 9.8
    assert detail.fix_version == "18.2.1"
    assert detail.risk_score == 98
    assert detail.risk_level == Severity.KRITISCH
    assert detail.description == "Langtext"
    assert detail.rationale == "CVSS 9.8 -> 98/100"
    assert detail.references == ["https://ref"]
    assert detail.sources == [SourceReference("osv", "https://o")]


def test_detail_lists_all_findings() -> None:
    uow, store = _ingested("Shop", "Blog")
    detail = GetAdvisoryDetail(uow, store).execute("CVE-2024-1")
    assert sorted(f.application_name for f in detail.findings) == ["Blog", "Shop"]
    finding = detail.findings[0]
    assert finding.component_name == "react"
    assert finding.found_version == "18.2.0"
    assert finding.ecosystem == "npm"
    assert finding.component_id is not None


def test_detail_without_document() -> None:
    uow, store = _ingested("Shop")
    store.documents.clear()
    detail = GetAdvisoryDetail(uow, store).execute("CVE-2024-1")
    assert detail.description == "XSS in react"
    assert detail.rationale == ""
    assert detail.references == []
    assert detail.sources == []


def test_unknown_advisory_raises_not_found() -> None:
    uow, store = _ingested("Shop")
    with pytest.raises(EntityNotFoundError):
        GetAdvisoryDetail(uow, store).execute("CVE-1999-0001")


def test_detail_shows_found_version_not_current() -> None:
    uow, store = _ingested("Shop")
    component = uow.components.list_all()[0]
    uow.components.update(Component(**{**component.__dict__, "version": "19.0.0"}))
    detail = GetAdvisoryDetail(uow, store).execute("CVE-2024-1")
    assert detail.findings[0].found_version == "18.2.0"
