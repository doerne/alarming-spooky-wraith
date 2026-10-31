from app.application.ingest import RunIngest
from app.application.inventory_use_cases import AddComponent, CreateApplication
from app.domain.inventory import Category, Component, Ecosystem
from app.domain.ports import OsvVuln
from tests.fakes import FakeAdvisoryStore, FakeOsvClient, InMemoryUnitOfWork


def _setup(vulns: list[OsvVuln]) -> tuple[InMemoryUnitOfWork, FakeOsvClient, FakeAdvisoryStore]:
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
    return uow, FakeOsvClient({"react": vulns}), FakeAdvisoryStore()


def test_cve_alias_becomes_advisory_id() -> None:
    vuln = OsvVuln(
        id="GHSA-xxxx",
        aliases=["CVE-2024-123"],
        summary="s",
        details="d",
        cvss_base=9.8,
        fixed_version="18.2.1",
        references=["https://nvd.nist.gov/vuln/detail/CVE-2024-123"],
    )
    uow, osv, store = _setup([vuln])
    result = RunIngest(uow, osv, store).execute()
    assert result.findings_found == 1
    finding = uow.findings.list()[0]
    assert finding.advisory_id == "CVE-2024-123"
    assert finding.application_id is not None
    assert "CVE-2024-123" in store.saved


def test_ghsa_only_keeps_ghsa_id() -> None:
    vuln = OsvVuln(
        id="GHSA-abcd",
        aliases=[],
        summary="s",
        details="d",
        cvss_base=None,
        fixed_version=None,
        references=[],
    )
    uow, osv, store = _setup([vuln])
    RunIngest(uow, osv, store).execute()
    finding = uow.findings.list()[0]
    assert finding.advisory_id == "GHSA-abcd"
    assert finding.risk.value == 0


def test_no_vulns_yields_zero_findings() -> None:
    uow, osv, store = _setup([])
    assert RunIngest(uow, osv, store).execute().findings_found == 0
    assert uow.findings.list() == []


def test_rerun_is_idempotent() -> None:
    vuln = OsvVuln(
        id="GHSA-x",
        aliases=["CVE-2024-1"],
        summary="s",
        details="d",
        cvss_base=7.5,
        fixed_version="1",
        references=[],
    )
    uow, osv, store = _setup([vuln])
    RunIngest(uow, osv, store).execute()
    RunIngest(uow, osv, store).execute()
    assert len(uow.findings.list()) == 1
