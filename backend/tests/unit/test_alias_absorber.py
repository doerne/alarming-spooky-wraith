from app.application.alias_absorber import AliasAbsorber
from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.vulnerability import Advisory, Finding, FindingStatus, RiskScore, Severity
from tests.fakes import FakeAdvisoryStore, InMemoryUnitOfWork

_CANONICAL = "GHSA-6q48-6c7w-9gw2"
_ALIAS = "PYSEC-2026-4320"


class _World:
    def __init__(self) -> None:
        self.uow = InMemoryUnitOfWork()
        self.store = FakeAdvisoryStore()
        application = self.uow.applications.add(Application(name="Shop"))
        assert application.id is not None
        self.application_id = application.id

    def component(self, name: str) -> int:
        component = self.uow.components.add(
            self.application_id, Component(name, "1.0", Category.LIBRARY, Ecosystem.PYPI, True)
        )
        assert component.id is not None
        return component.id

    def advisory(self, advisory_id: str) -> None:
        self.uow.advisories.upsert(
            Advisory(advisory_id, None, "t", "d", 7.5, None, [], f"advisories/{advisory_id}.md")
        )
        self.store.saved[advisory_id] = "body"

    def finding(
        self, advisory_id: str, component_id: int, status: FindingStatus, comment: str = ""
    ) -> None:
        self.uow.findings.upsert(
            Finding(
                advisory_id=advisory_id,
                component_id=component_id,
                application_id=self.application_id,
                found_version="1.0",
                risk=RiskScore(value=75, level=Severity.HOCH, rationale=""),
                status=status,
                comment=comment,
            )
        )

    def absorb(self) -> None:
        AliasAbsorber(self.uow, self.store).absorb(_CANONICAL, [_ALIAS])


def test_absorber_moves_findings_and_deletes_alias() -> None:
    world = _World()
    world.advisory(_CANONICAL)
    world.advisory(_ALIAS)
    certifi = world.component("certifi")
    world.finding(_ALIAS, certifi, FindingStatus.ACCEPTED, "Risiko akzeptiert")
    world.absorb()
    [finding] = world.uow.findings.list()
    assert (finding.advisory_id, finding.status, finding.comment) == (
        _CANONICAL,
        FindingStatus.ACCEPTED,
        "Risiko akzeptiert",
    )
    assert world.uow.advisories.find(_ALIAS) is None
    assert _ALIAS not in world.store.saved
    assert world.uow.advisory_aliases.resolve(_ALIAS) == _CANONICAL


def test_absorber_merges_triage_into_open_canonical() -> None:
    world = _World()
    world.advisory(_CANONICAL)
    world.advisory(_ALIAS)
    certifi = world.component("certifi")
    world.finding(_CANONICAL, certifi, FindingStatus.OPEN, "erst mal ansehen")
    world.finding(_ALIAS, certifi, FindingStatus.IN_PROGRESS, "Upgrade in PR #3")
    world.absorb()
    [finding] = world.uow.findings.list()
    assert finding.advisory_id == _CANONICAL
    assert finding.status == FindingStatus.IN_PROGRESS
    assert finding.comment == "erst mal ansehen\n\nUpgrade in PR #3"


def test_absorber_keeps_canonical_status_when_not_open() -> None:
    world = _World()
    world.advisory(_CANONICAL)
    world.advisory(_ALIAS)
    certifi = world.component("certifi")
    world.finding(_CANONICAL, certifi, FindingStatus.FALSE_POSITIVE)
    world.finding(_ALIAS, certifi, FindingStatus.IN_PROGRESS, "PR #3")
    world.absorb()
    [finding] = world.uow.findings.list()
    assert finding.status == FindingStatus.FALSE_POSITIVE
    assert finding.comment == "PR #3"


def test_absorber_records_alias_without_advisory() -> None:
    world = _World()
    world.advisory(_CANONICAL)
    world.absorb()
    assert world.uow.advisory_aliases.resolve(_ALIAS) == _CANONICAL
    assert world.uow.advisories.find(_CANONICAL) is not None


def test_absorber_repoints_chains_and_drops_alias_row_of_canonical() -> None:
    world = _World()
    world.uow.advisory_aliases.save("PYSEC-1", _CANONICAL)
    world.uow.advisory_aliases.save("CVE-2026-1", "OLD-ID")
    world.advisory("CVE-2026-1")
    AliasAbsorber(world.uow, world.store).absorb("CVE-2026-1", [_CANONICAL])
    assert world.uow.advisory_aliases.resolve("PYSEC-1") == "CVE-2026-1"
    assert world.uow.advisory_aliases.resolve(_CANONICAL) == "CVE-2026-1"
    assert world.uow.advisory_aliases.resolve("CVE-2026-1") is None
