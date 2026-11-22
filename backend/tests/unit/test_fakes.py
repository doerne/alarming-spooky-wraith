from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.domain.errors import EntityNotFoundError
from app.domain.inventory import Category, Component, Ecosystem
from app.domain.sbom import Sbom, SbomVersion
from app.domain.vulnerability import (
    Finding,
    FindingResolution,
    FindingStatus,
    ResolutionSource,
    RiskScore,
    Severity,
)
from tests.fakes import (
    InMemoryComponentRepository,
    InMemoryFindingRepository,
    InMemoryUnitOfWork,
)


def _finding(status: FindingStatus = FindingStatus.OPEN, comment: str = "") -> Finding:
    return Finding(
        advisory_id="CVE-2024-1",
        component_id=1,
        application_id=1,
        found_version="1.0.0",
        risk=RiskScore(value=50, level=Severity.MITTEL, rationale="r"),
        status=status,
        comment=comment,
    )


def test_fake_upsert_keeps_triage_status() -> None:
    repository = InMemoryFindingRepository()
    repository.upsert(_finding(FindingStatus.FALSE_POSITIVE, "nein"))
    again = repository.upsert(_finding())
    stored = repository.list()[0]
    assert stored.status == FindingStatus.FALSE_POSITIVE
    assert stored.comment == "nein"
    assert again.status == FindingStatus.FALSE_POSITIVE


def _version(sbom_id: int, label: str, *, is_current: bool) -> SbomVersion:

    return SbomVersion(
        sbom_id=sbom_id,
        label=label,
        uploaded_at=datetime(2026, 11, 21, tzinfo=UTC),
        serial_number=None,
        is_current=is_current,
        entries=(),
    )


def test_fake_sbom_repository_finds_by_name_per_application() -> None:

    uow = InMemoryUnitOfWork()
    uow.sboms.add(Sbom(application_id=1, name="backend"))
    uow.sboms.add(Sbom(application_id=2, name="backend"))
    found = uow.sboms.find_by_name(1, "backend")
    assert found is not None
    assert found.application_id == 1
    assert uow.sboms.find_by_name(1, "frontend") is None


def test_fake_sbom_delete_removes_versions() -> None:

    uow = InMemoryUnitOfWork()
    sbom = uow.sboms.add(Sbom(application_id=1, name="backend"))
    assert sbom.id is not None
    uow.sbom_versions.add(_version(sbom.id, "v1", is_current=True))
    uow.sboms.delete(sbom.id)
    assert uow.sbom_versions.list_for_sbom(sbom.id) == []
    with pytest.raises(EntityNotFoundError):
        uow.sboms.get(sbom.id)


def test_fake_version_repository_lists_newest_first_and_archives() -> None:

    uow = InMemoryUnitOfWork()
    first = uow.sbom_versions.add(_version(1, "v1", is_current=True))
    second = uow.sbom_versions.add(_version(1, "v2", is_current=True))
    assert first.id is not None
    assert [version.label for version in uow.sbom_versions.list_for_sbom(1)] == ["v2", "v1"]
    uow.sbom_versions.archive(first.id)
    current = uow.sbom_versions.current_for_sbom(1)
    assert current is not None
    assert current.id == second.id
    assert uow.sbom_versions.get(first.id).is_current is False


def test_fake_finding_delete_for_components() -> None:
    repository = InMemoryFindingRepository()
    repository.upsert(_finding())
    other = _finding()
    other.component_id = 2
    repository.upsert(other)
    repository.delete_for_components([1])
    assert [finding.component_id for finding in repository.list()] == [2]


def test_fake_component_delete_and_list_for_sbom() -> None:

    repository = InMemoryComponentRepository()
    base = Component("react", "18.2.0", Category.LIBRARY, Ecosystem.NPM, True)

    manual = repository.add(1, base)
    from_sbom = repository.add(1, replace(base, sbom_id=7))
    assert [component.id for component in repository.list_for_sbom(7)] == [from_sbom.id]
    assert manual.id is not None
    repository.delete_many([manual.id])
    assert [component.id for component in repository.list_all()] == [from_sbom.id]


_NOW = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)
_EARLIER = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)


def _resolution(status: FindingStatus, closed_at: datetime | None) -> FindingResolution:
    return FindingResolution(
        status=status,
        resolved_at=_NOW,
        text="erledigt",
        source=ResolutionSource.REPORTED,
        closed_at=closed_at,
    )


def test_fake_resolve_writes_closed_at_of_resolution() -> None:
    repository = InMemoryFindingRepository()
    saved = repository.upsert(_finding())
    assert saved.id is not None
    repository.resolve(saved.id, _resolution(FindingStatus.FIXED, _NOW))
    assert repository.list()[0].closed_at == _NOW


def test_fake_resolve_overwrites_closed_at_with_resolution_value() -> None:
    repository = InMemoryFindingRepository()
    saved = repository.upsert(_finding())
    assert saved.id is not None
    repository.save_report(replace(saved, status=FindingStatus.ACCEPTED, closed_at=_EARLIER))
    repository.resolve(saved.id, _resolution(FindingStatus.FIXED, None))
    assert repository.list()[0].closed_at is None


def test_fake_save_report_persists_closed_at_and_first_seen_at() -> None:
    repository = InMemoryFindingRepository()
    saved = repository.upsert(_finding())
    repository.save_report(replace(saved, closed_at=_NOW, first_seen_at=_EARLIER))
    stored = repository.list()[0]
    assert stored.closed_at == _NOW
    assert stored.first_seen_at == _EARLIER
