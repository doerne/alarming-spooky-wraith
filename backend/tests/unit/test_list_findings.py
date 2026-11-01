from datetime import UTC, datetime

from app.application.component_matching import ComponentMatcher
from app.application.ingest import RunIngest
from app.application.inventory_use_cases import AddComponent, CreateApplication
from app.application.list_findings import NO_ECOSYSTEM, FindingFilter, ListFindings
from app.application.source_registry import SourceRegistry
from app.domain.inventory import Category, Component, Ecosystem
from app.domain.ports import SourceVuln
from app.domain.vulnerability import (
    Advisory,
    Finding,
    FindingStatus,
    RiskScore,
    Severity,
)
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
    views = ListFindings(_ingested_uow()).execute().items
    assert [v.risk_score for v in views] == [98, 50]
    assert views[0].risk_level == Severity.KRITISCH


def test_finding_view_joins_component_and_application() -> None:
    top = ListFindings(_ingested_uow()).execute().items[0]
    assert top.advisory_id == "CVE-2024-1"
    assert top.application_name == "Shop"
    assert top.component_name == "react"
    assert top.component_version == "18.2.0"
    assert top.ecosystem == "npm"
    assert top.fix_version == "9.9.9"


_LEVEL_BY_SCORE = {98: Severity.KRITISCH, 75: Severity.HOCH, 50: Severity.MITTEL}


def _add_finding(
    uow: InMemoryUnitOfWork,
    component: Component,
    advisory_id: str,
    score: int,
    status: FindingStatus = FindingStatus.OPEN,
) -> None:
    uow.advisories.upsert(
        Advisory(advisory_id, advisory_id, f"Titel {advisory_id}", "", None, None, [], "")
    )
    assert component.id is not None
    assert component.application_id is not None
    uow.findings.upsert(
        Finding(
            advisory_id=advisory_id,
            component_id=component.id,
            application_id=component.application_id,
            found_version=component.version,
            risk=RiskScore(score, _LEVEL_BY_SCORE[score], ""),
            status=status,
        )
    )


def _seeded() -> tuple[InMemoryUnitOfWork, int, int]:
    """Shop: react (npm) mit CVE-1 kritisch, CVE-2 mittel/false_positive.
    Blog: redis (ohne Ökosystem) mit CVE-3 hoch, django (PyPI) mit CVE-4 mittel."""
    uow = InMemoryUnitOfWork()
    shop = CreateApplication(uow).execute(name="Shop")
    blog = CreateApplication(uow).execute(name="Blog")
    assert shop.id is not None
    assert blog.id is not None

    def add(app_id: int, name: str, ecosystem: Ecosystem | None) -> Component:
        component = Component(name, "1.0.0", Category.LIBRARY, ecosystem, True)
        return AddComponent(uow).execute(application_id=app_id, component=component)

    react = add(shop.id, "react", Ecosystem.NPM)
    redis = add(blog.id, "redis", None)
    django = add(blog.id, "django", Ecosystem.PYPI)
    _add_finding(uow, react, "CVE-2024-1", 98)
    _add_finding(uow, react, "CVE-2024-2", 50, FindingStatus.FALSE_POSITIVE)
    _add_finding(uow, redis, "CVE-2024-3", 75)
    _add_finding(uow, django, "CVE-2024-4", 50)
    return uow, shop.id, blog.id


def _ids(uow: InMemoryUnitOfWork, finding_filter: FindingFilter) -> list[str]:
    return [view.advisory_id for view in ListFindings(uow).execute(finding_filter).items]


def test_filter_by_severity() -> None:
    uow, _, _ = _seeded()
    severities = frozenset({Severity.KRITISCH, Severity.HOCH})
    assert _ids(uow, FindingFilter(severities=severities)) == ["CVE-2024-1", "CVE-2024-3"]


def test_filter_by_status() -> None:
    uow, _, _ = _seeded()
    statuses = frozenset({FindingStatus.FALSE_POSITIVE})
    assert _ids(uow, FindingFilter(statuses=statuses)) == ["CVE-2024-2"]


def test_filter_by_ecosystem_and_none() -> None:
    uow, _, _ = _seeded()
    ecosystems = frozenset({"PyPI", NO_ECOSYSTEM})
    assert _ids(uow, FindingFilter(ecosystems=ecosystems)) == ["CVE-2024-3", "CVE-2024-4"]


def test_filters_combine_with_and() -> None:
    uow, _, blog_id = _seeded()
    finding_filter = FindingFilter(application_id=blog_id, severities=frozenset({Severity.MITTEL}))
    assert _ids(uow, finding_filter) == ["CVE-2024-4"]


def test_query_matches_id_title_component_case_insensitive() -> None:
    uow, _, _ = _seeded()
    assert _ids(uow, FindingFilter(query="REDIS")) == ["CVE-2024-3"]
    assert _ids(uow, FindingFilter(query="titel cve-2024-4")) == ["CVE-2024-4"]
    assert _ids(uow, FindingFilter(query="2024-1")) == ["CVE-2024-1"]


def test_query_is_trimmed_and_literal() -> None:
    uow, _, _ = _seeded()
    assert _ids(uow, FindingFilter(query="  react  ")) == ["CVE-2024-1", "CVE-2024-2"]
    assert _ids(uow, FindingFilter(query="%")) == []


def test_unfiltered_total_respects_application_scope() -> None:
    uow, shop_id, _ = _seeded()
    result = ListFindings(uow).execute(
        FindingFilter(application_id=shop_id, severities=frozenset({Severity.KRITISCH}))
    )
    assert len(result.items) == 1
    assert result.unfiltered_total == 2


def test_empty_scope() -> None:
    uow = InMemoryUnitOfWork()
    result = ListFindings(uow).execute(FindingFilter(query="x"))
    assert result.items == []
    assert result.unfiltered_total == 0
