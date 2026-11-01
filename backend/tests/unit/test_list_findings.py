from datetime import UTC, datetime

from app.application.component_matching import ComponentMatcher
from app.application.ingest import RunIngest
from app.application.inventory_use_cases import AddComponent, CreateApplication
from app.application.list_findings import ListFindings
from app.application.source_registry import SourceRegistry
from app.domain.inventory import Category, Component, Ecosystem
from app.domain.ports import SourceVuln
from app.domain.vulnerability import Severity
from app.infrastructure.univers_matcher import UniversVersionMatcher
from tests.fakes import FakeAdvisoryStore, FakePackageSource, InMemoryUnitOfWork, descriptor


def _vuln(advisory: str, base: float) -> SourceVuln:
    return SourceVuln(
        source_key="osv",
        url="https://osv.dev/vulnerability",
        id=advisory,
        aliases=[advisory],
        summary=f"summary {advisory}",
        details="d",
        cvss_base=base,
        fixed_version="9.9.9",
        references=[],
    )


def _ingested_uow() -> InMemoryUnitOfWork:
    uow = InMemoryUnitOfWork()
    application = CreateApplication(uow).execute(name="Shop")
    assert application.id is not None
    AddComponent(uow).execute(
        application_id=application.id,
        component=Component(
            name="react",
            version="18.2.0",
            category=Category.LIBRARY,
            ecosystem=Ecosystem.NPM,
            direct=True,
        ),
    )
    osv = FakePackageSource(
        descriptor("osv"), {"react": [_vuln("CVE-2024-1", 9.8), _vuln("CVE-2024-2", 5.0)]}
    )
    RunIngest(
        uow,
        SourceRegistry([osv]),
        ComponentMatcher(UniversVersionMatcher()),
        FakeAdvisoryStore(),
        lambda: datetime.now(UTC),
    ).execute()
    return uow


def test_findings_are_sorted_by_risk_score_descending() -> None:
    views = ListFindings(_ingested_uow()).execute()
    assert [v.risk_score for v in views] == [98, 50]
    assert views[0].risk_level == Severity.KRITISCH


def test_finding_view_joins_component_and_application() -> None:
    top = ListFindings(_ingested_uow()).execute()[0]
    assert top.advisory_id == "CVE-2024-1"
    assert top.application_name == "Shop"
    assert top.component_name == "react"
    assert top.component_version == "18.2.0"
    assert top.ecosystem == "npm"
    assert top.fix_version == "9.9.9"
