from datetime import UTC, datetime

from app.application.component_matching import ComponentMatcher
from app.application.ingest import IngestResult, RunIngest
from app.application.inventory_use_cases import AddComponent, CreateApplication
from app.application.source_registry import SourceRegistry
from app.domain.errors import SourceAccessError
from app.domain.inventory import Category, Component, Ecosystem
from app.domain.ports import AffectedPackage, RangeEvent, SourceVuln
from app.domain.sources import (
    ApiKeyRequirement,
    MatchScope,
    RunStatus,
    SourceKind,
    SourceSetting,
)
from app.domain.vulnerability import ADVISORY_TITLE_MAX_LENGTH, FindingStatus
from app.infrastructure.univers_matcher import UniversVersionMatcher
from tests.fakes import (
    FakeAdvisoryStore,
    FakeBulkSource,
    FakePackageSource,
    InMemoryUnitOfWork,
    VulnerabilitySourceFake,
    descriptor,
)

_NOW = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
_REACT_RANGE = (RangeEvent("introduced", "0"), RangeEvent("fixed", "18.2.1"))


def _vuln(source_key: str = "osv", **overrides: object) -> SourceVuln:
    values: dict[str, object] = {
        "source_key": source_key,
        "id": "GHSA-xxxx",
        "aliases": ["CVE-2024-123"],
        "summary": "XSS",
        "details": "d",
        "cvss_base": 9.8,
        "fixed_version": "18.2.1",
        "references": ["https://nvd.nist.gov/vuln/detail/CVE-2024-123"],
        "url": f"https://{source_key}.example.org/x",
    }
    values.update(overrides)
    return SourceVuln(**values)  # type: ignore[arg-type]


def _uow(*components: Component) -> InMemoryUnitOfWork:
    uow = InMemoryUnitOfWork()
    application = CreateApplication(uow).execute(name="Shop")
    assert application.id is not None
    for component in components:
        AddComponent(uow).execute(application_id=application.id, component=component)
    return uow


def _component(name: str, ecosystem: Ecosystem | None, version: str = "18.2.0") -> Component:
    return Component(
        name=name, version=version, category=Category.LIBRARY, ecosystem=ecosystem, direct=True
    )


_REACT = _component("react", Ecosystem.NPM)


def _run(
    uow: InMemoryUnitOfWork,
    *sources: VulnerabilitySourceFake,
    store: FakeAdvisoryStore | None = None,
) -> IngestResult:
    matcher = ComponentMatcher(UniversVersionMatcher())
    registry = SourceRegistry(list(sources))
    return RunIngest(uow, registry, matcher, store or FakeAdvisoryStore(), lambda: _NOW).execute()


def _result_of(result: IngestResult, key: str) -> RunStatus:
    return next(item.status for item in result.sources if item.source_key == key)


def test_cve_alias_becomes_advisory_id() -> None:
    uow = _uow(_REACT)
    store = FakeAdvisoryStore()
    result = _run(uow, FakePackageSource(descriptor("osv"), {"react": [_vuln()]}), store=store)
    assert result.findings_found == 1
    assert result.components_scanned == 1
    finding = uow.findings.list()[0]
    assert finding.advisory_id == "CVE-2024-123"
    assert "CVE-2024-123" in store.saved


def test_ghsa_only_keeps_ghsa_id() -> None:
    uow = _uow(_REACT)
    vuln = _vuln(id="GHSA-abcd", aliases=[], cvss_base=None)
    _run(uow, FakePackageSource(descriptor("osv"), {"react": [vuln]}))
    finding = uow.findings.list()[0]
    assert finding.advisory_id == "GHSA-abcd"
    assert finding.risk.value == 0


def test_rerun_is_idempotent_and_keeps_triage() -> None:
    uow = _uow(_REACT)
    source = FakePackageSource(descriptor("osv"), {"react": [_vuln()]})
    _run(uow, source)
    uow.findings.list()[0].status = FindingStatus.FALSE_POSITIVE
    _run(uow, source)
    assert len(uow.findings.list()) == 1
    assert uow.findings.list()[0].status == FindingStatus.FALSE_POSITIVE


def test_disabled_source_is_skipped() -> None:
    uow = _uow(_REACT)
    uow.source_settings.save(SourceSetting(source_key="osv", enabled=False))
    source = FakePackageSource(descriptor("osv"), {"react": [_vuln()]})
    result = _run(uow, source)
    assert source.calls == []
    assert _result_of(result, "osv") == RunStatus.SKIPPED
    stored = uow.source_settings.get("osv")
    assert stored is not None
    assert stored.last_message == "deaktiviert"


def test_required_key_missing_is_skipped() -> None:
    uow = _uow(_REACT)
    source = FakePackageSource(descriptor("snyk", requirement=ApiKeyRequirement.REQUIRED))
    result = _run(uow, source)
    assert source.calls == []
    assert _result_of(result, "snyk") == RunStatus.SKIPPED
    stored = uow.source_settings.get("snyk")
    assert stored is not None
    assert stored.last_message == "API-Key fehlt"


def test_api_key_is_passed_to_source() -> None:
    uow = _uow(_REACT)
    uow.source_settings.save(SourceSetting(source_key="snyk", api_key="secret"))
    source = FakePackageSource(descriptor("snyk", requirement=ApiKeyRequirement.REQUIRED))
    _run(uow, source)
    assert source.calls == [("react", "secret")]


def test_failing_source_does_not_stop_run() -> None:
    uow = _uow(_REACT)
    broken = FakePackageSource(descriptor("broken"), error=RuntimeError("secret=abc"))
    working = FakePackageSource(descriptor("osv"), {"react": [_vuln()]})
    result = _run(uow, broken, working)
    assert _result_of(result, "broken") == RunStatus.ERROR
    assert _result_of(result, "osv") == RunStatus.OK
    assert result.findings_found == 1
    stored = uow.source_settings.get("broken")
    assert stored is not None
    assert stored.last_message == "Unerwarteter Fehler (RuntimeError)"
    assert stored.last_run_at == _NOW


def test_same_cve_from_two_sources_gives_one_finding() -> None:
    uow = _uow(_REACT)
    osv = FakePackageSource(descriptor("osv"), {"react": [_vuln("osv", cvss_base=5.0)]})
    nvd_like = FakePackageSource(
        descriptor("ghsa"), {"react": [_vuln("ghsa", id="CVE-2024-123", aliases=[])]}
    )
    result = _run(uow, osv, nvd_like)
    assert result.findings_found == 1
    assert len(uow.findings.list()) == 1
    assert uow.findings.list()[0].risk.value == 50


def test_bulk_source_matches_by_version() -> None:
    uow = _uow(_REACT, _component("vue", Ecosystem.NPM, version="3.0.0"))
    react_vuln = _vuln(
        "pypa", affected=(AffectedPackage("npm", "react", _REACT_RANGE),), id="CVE-2024-1"
    )
    other = _vuln(
        "pypa",
        id="CVE-2024-2",
        aliases=[],
        affected=(AffectedPackage("npm", "vue", (RangeEvent("introduced", "4.0.0"),)),),
    )
    bulk = FakeBulkSource(descriptor("pypa", kind=SourceKind.BULK), [react_vuln, other])
    result = _run(uow, bulk)
    assert bulk.loads == 1
    assert [finding.advisory_id for finding in uow.findings.list()] == ["CVE-2024-1"]
    assert result.sources[0].findings == 1


def test_product_scope_only_sees_components_without_ecosystem() -> None:
    uow = _uow(_REACT, _component("mariadb", None, version="11.4.2"))
    source = FakePackageSource(descriptor("nvd", scope=MatchScope.PRODUCT))
    _run(uow, source)
    assert [name for name, _ in source.calls] == ["mariadb"]


def test_product_results_are_version_checked() -> None:
    uow = _uow(_component("mariadb", None, version="11.4.2"))
    fixed_already = _vuln(
        "nvd",
        affected=(
            AffectedPackage(
                None, "mariadb", (RangeEvent("introduced", "0"), RangeEvent("fixed", "11.4.0"))
            ),
        ),
    )
    source = FakePackageSource(
        descriptor("nvd", scope=MatchScope.PRODUCT), {"mariadb": [fixed_already]}
    )
    assert _run(uow, source).findings_found == 0


def test_package_scope_respects_descriptor_ecosystems() -> None:
    uow = _uow(_REACT)
    source = FakePackageSource(descriptor("packagist", ecosystems=frozenset({"Packagist"})))
    _run(uow, source)
    assert source.calls == []


def test_unsafe_advisory_id_is_skipped() -> None:
    uow = _uow(_REACT)
    evil = _vuln(id="../x", aliases=[])
    source = FakePackageSource(descriptor("osv"), {"react": [evil, _vuln()]})
    store = FakeAdvisoryStore(reject={"../x"})
    result = _run(uow, source, store=store)
    assert _result_of(result, "osv") == RunStatus.OK
    assert [finding.advisory_id for finding in uow.findings.list()] == ["CVE-2024-123"]


def test_progress_is_committed_per_source() -> None:
    uow = _uow(_REACT)
    commits_before = uow.commits
    _run(uow, FakePackageSource(descriptor("osv")), FakePackageSource(descriptor("ghsa")))
    assert uow.commits - commits_before >= 3


def test_no_vulns_yields_zero_findings() -> None:
    uow = _uow(_REACT)
    assert _run(uow, FakePackageSource(descriptor("osv"))).findings_found == 0
    assert uow.findings.list() == []


def test_source_access_error_message_is_shown() -> None:
    uow = _uow(_REACT)
    source = FakePackageSource(descriptor("osv"), error=SourceAccessError("Rate-Limit erreicht"))
    _run(uow, source)
    stored = uow.source_settings.get("osv")
    assert stored is not None
    assert stored.last_message == "Rate-Limit erreicht"


def test_bulk_source_gets_names_of_components_in_scope() -> None:
    uow = _uow(_REACT, _component("MariaDB", None, version="11.4.2"))
    bulk = FakeBulkSource(descriptor("cve-org", kind=SourceKind.BULK, scope=MatchScope.PRODUCT))
    _run(uow, bulk)
    assert bulk.names == [frozenset({"mariadb"})]


def test_long_summary_is_shortened_for_title() -> None:
    uow = _uow(_REACT)
    long_text = "A" * 2000
    store = FakeAdvisoryStore()
    source = FakePackageSource(descriptor("osv"), {"react": [_vuln(summary=long_text)]})
    _run(uow, source, store=store)
    advisory = uow.advisories.get("CVE-2024-123")
    assert len(advisory.title) <= ADVISORY_TITLE_MAX_LENGTH
    assert advisory.title.endswith("…")
    assert advisory.description == long_text


def test_long_fix_version_is_dropped() -> None:
    uow = _uow(_REACT)
    source = FakePackageSource(descriptor("osv"), {"react": [_vuln(fixed_version="9" * 300)]})
    _run(uow, source)
    assert uow.advisories.get("CVE-2024-123").fixed_version is None


class _UserChangesDuringQuery(FakePackageSource):
    """Simuliert: Nutzer deaktiviert die Quelle und hinterlegt einen Key, während sie läuft."""

    def __init__(self, uow: InMemoryUnitOfWork) -> None:
        super().__init__(descriptor("osv"))
        self._uow = uow

    def query(self, component: Component, api_key: str | None) -> list[SourceVuln]:
        self._uow.source_settings.save(
            SourceSetting(source_key="osv", enabled=False, api_key="new-key")
        )
        return super().query(component, api_key)


def test_user_changes_during_run_are_kept() -> None:
    uow = _uow(_REACT)
    _run(uow, _UserChangesDuringQuery(uow))
    stored = uow.source_settings.get("osv")
    assert stored is not None
    assert stored.enabled is False
    assert stored.api_key == "new-key"
    assert stored.last_status == RunStatus.OK


def test_known_values_survive_a_run_without_them() -> None:
    uow = _uow(_REACT)
    with_score = FakePackageSource(descriptor("osv"), {"react": [_vuln(cvss_base=9.8)]})
    _run(uow, with_score)
    without_score = FakePackageSource(
        descriptor("osv"), {"react": [_vuln(cvss_base=None, fixed_version=None)]}
    )
    _run(uow, without_score)
    advisory = uow.advisories.get("CVE-2024-123")
    assert advisory.cvss_base == 9.8
    assert advisory.fixed_version == "18.2.1"
    assert uow.findings.list()[0].risk.value == 98


class _FailsFor(FakePackageSource):
    def __init__(self, failing: str, vulns_by_name: dict[str, list[SourceVuln]]) -> None:
        super().__init__(descriptor("osv"), vulns_by_name)
        self._failing = failing

    def query(self, component: Component, api_key: str | None) -> list[SourceVuln]:
        if component.name == self._failing:
            raise SourceAccessError("Rate-Limit erreicht")
        return super().query(component, api_key)


def test_one_failing_component_keeps_other_hits() -> None:
    uow = _uow(_REACT, _component("vue", Ecosystem.NPM))
    result = _run(uow, _FailsFor("vue", {"react": [_vuln()]}))
    assert result.findings_found == 1
    stored = uow.source_settings.get("osv")
    assert stored is not None
    assert stored.last_status == RunStatus.OK
    assert stored.last_message == "1 von 2 Abfragen fehlgeschlagen: Rate-Limit erreicht"


def test_all_components_failing_is_an_error() -> None:
    uow = _uow(_REACT)
    result = _run(uow, _FailsFor("react", {}))
    assert _result_of(result, "osv") == RunStatus.ERROR
