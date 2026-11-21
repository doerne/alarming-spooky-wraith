from datetime import UTC, datetime

import pytest

from app.application.sbom_use_cases import SbomUploadResult, UploadSbomVersion
from app.domain.errors import DuplicateSbomVersionError, EntityNotFoundError, InvalidValueError
from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.sbom import ParsedSbom, SbomEntry
from app.domain.vulnerability import Finding, FindingStatus, RiskScore, Severity
from tests.fakes import FakeSbomParser, InMemoryUnitOfWork

_NOW = datetime(2026, 11, 21, 9, 30, tzinfo=UTC)
_DOCUMENT: dict[str, object] = {"bomFormat": "CycloneDX"}
_REACT = SbomEntry("react", "18.2.0", Category.LIBRARY, Ecosystem.NPM, True, None)
_LODASH = SbomEntry("lodash", "4.17.21", Category.LIBRARY, Ecosystem.NPM, False, None)
_OPENSSL = SbomEntry("openssl", "3.0.11", Category.LIBRARY, None, False, None)


def _parsed(
    *entries: SbomEntry, serial: str | None = None, label: str | None = "1.0.0", skipped: int = 0
) -> ParsedSbom:
    return ParsedSbom(entries=entries, serial_number=serial, suggested_label=label, skipped=skipped)


def _application(uow: InMemoryUnitOfWork) -> int:
    application = uow.applications.add(Application(name="Shop"))
    assert application.id is not None
    return application.id


def _upload(
    uow: InMemoryUnitOfWork,
    application_id: int,
    parsed: ParsedSbom,
    *,
    name: str = "backend-image",
    label: str | None = None,
) -> SbomUploadResult:
    use_case = UploadSbomVersion(uow, FakeSbomParser(parsed), lambda: _NOW)
    return use_case.execute(
        application_id=application_id, name=name, label=label, document=_DOCUMENT
    )


def _finding_for(uow: InMemoryUnitOfWork, component: Component) -> Finding:
    assert component.id is not None
    assert component.application_id is not None
    return uow.findings.upsert(
        Finding(
            advisory_id="CVE-2024-1",
            component_id=component.id,
            application_id=component.application_id,
            found_version=component.version,
            risk=RiskScore(value=80, level=Severity.HOCH, rationale="r"),
            status=FindingStatus.ACCEPTED,
            comment="geprüft",
        )
    )


def test_first_upload_creates_sbom_version_and_components() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    result = _upload(uow, application_id, _parsed(_REACT, _OPENSSL, skipped=2))
    assert (result.added, result.removed, result.kept, result.unchecked, result.skipped) == (
        2,
        0,
        0,
        1,
        2,
    )
    assert result.version.is_current
    assert result.version.label == "1.0.0"
    components = uow.components.list_for_application(application_id)
    assert {c.sbom_id for c in components} == {result.sbom.id}
    assert {(c.name, c.checked) for c in components} == {("react", True), ("openssl", False)}
    assert uow.commits == 1


def test_duplicates_in_document_become_one_component() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    duplicate = SbomEntry("react", "18.2.0", Category.LIBRARY, Ecosystem.NPM, False, None)
    result = _upload(uow, application_id, _parsed(duplicate, _REACT))
    assert result.added == 1
    assert len(result.version.entries) == 1
    assert uow.components.list_for_application(application_id)[0].direct is True


def test_second_upload_archives_previous_version() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    first = _upload(uow, application_id, _parsed(_REACT, label="1.0.0"))
    second = _upload(uow, application_id, _parsed(_REACT, label="1.1.0"))
    assert second.sbom.id == first.sbom.id
    assert second.sbom.id is not None
    versions = uow.sbom_versions.list_for_sbom(second.sbom.id)
    assert [(v.label, v.is_current) for v in versions] == [("1.1.0", True), ("1.0.0", False)]


def test_kept_component_keeps_finding_status() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    _upload(uow, application_id, _parsed(_REACT))
    react = uow.components.list_for_application(application_id)[0]
    _finding_for(uow, react)
    result = _upload(uow, application_id, _parsed(_REACT, _LODASH, label="1.1.0"))
    assert (result.kept, result.added, result.removed) == (1, 1, 0)
    finding = uow.findings.list()[0]
    assert finding.component_id == react.id
    assert finding.status == FindingStatus.ACCEPTED
    assert finding.comment == "geprüft"


def test_manual_components_untouched() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    manual = uow.components.add(
        application_id, Component("react", "18.2.0", Category.LIBRARY, Ecosystem.NPM, True)
    )
    _upload(uow, application_id, _parsed(_REACT))
    _upload(uow, application_id, _parsed(_LODASH, label="1.1.0"))
    names = sorted(
        (c.name, c.sbom_id is None) for c in uow.components.list_for_application(application_id)
    )
    assert names == [("lodash", False), ("react", True)]
    assert uow.components.get(manual.id or 0) == manual


def test_same_serial_as_current_is_rejected() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    first = _upload(uow, application_id, _parsed(_REACT, serial="urn:uuid:1"))
    commits = uow.commits
    with pytest.raises(DuplicateSbomVersionError):
        _upload(uow, application_id, _parsed(_REACT, serial="urn:uuid:1"))
    assert uow.commits == commits
    assert first.sbom.id is not None
    assert len(uow.sbom_versions.list_for_sbom(first.sbom.id)) == 1


def test_unknown_application_raises_not_found() -> None:
    uow = InMemoryUnitOfWork()
    with pytest.raises(EntityNotFoundError):
        _upload(uow, 999, _parsed(_REACT))
    assert uow.commits == 0


def test_label_falls_back_to_suggestion_then_clock() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    explicit = _upload(uow, application_id, _parsed(_REACT), name="a", label="  v2.0  ")
    suggested = _upload(uow, application_id, _parsed(_REACT, label="1.4.0"), name="b", label=" ")
    from_clock = _upload(uow, application_id, _parsed(_REACT, label=None), name="c")
    assert explicit.version.label == "v2.0"
    assert suggested.version.label == "1.4.0"
    assert from_clock.version.label == "2026-11-21 09:30"


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
def test_invalid_name_is_rejected(name: str) -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    with pytest.raises(InvalidValueError):
        _upload(uow, application_id, _parsed(_REACT), name=name)


def test_kept_component_takes_new_category_direct_and_checked() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    _upload(uow, application_id, _parsed(_REACT))
    before = uow.components.list_for_application(application_id)[0]
    _finding_for(uow, before)
    changed = SbomEntry("react", "18.2.0", Category.FRAMEWORK, Ecosystem.NPM, False, None)
    _upload(uow, application_id, _parsed(changed, label="1.1.0"))
    after = uow.components.list_for_application(application_id)[0]
    assert after.id == before.id
    assert (after.category, after.direct) == (Category.FRAMEWORK, False)
    assert uow.findings.list()[0].component_id == before.id


def test_clock_is_read_once_per_upload() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    times = iter(
        [
            datetime(2026, 11, 21, 9, 30, 59, tzinfo=UTC),
            datetime(2026, 11, 21, 9, 31, 0, tzinfo=UTC),
        ]
    )
    use_case = UploadSbomVersion(
        uow, FakeSbomParser(_parsed(_REACT, label=None)), lambda: next(times)
    )
    result = use_case.execute(
        application_id=application_id, name="backend", label=None, document=_DOCUMENT
    )
    assert result.version.label == "2026-11-21 09:30"
    assert result.version.uploaded_at.minute == 30


def test_unchanged_kept_components_are_not_rewritten() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    _upload(uow, application_id, _parsed(_REACT, _LODASH))
    updates: list[Component] = []
    original_update = uow.components.update

    def counting_update(component: Component) -> Component:
        updates.append(component)
        return original_update(component)

    uow.components.update = counting_update  # type: ignore[method-assign]
    changed_lodash = SbomEntry("lodash", "4.17.21", Category.LIBRARY, Ecosystem.NPM, True, None)
    _upload(uow, application_id, _parsed(_REACT, changed_lodash, label="1.1.0"))
    assert [component.name for component in updates] == ["lodash"]


def test_removed_component_with_findings_is_retired() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    _upload(uow, application_id, _parsed(_REACT))
    react = uow.components.list_for_application(application_id)[0]
    _finding_for(uow, react)
    result = _upload(uow, application_id, _parsed(_LODASH, label="1.1.0"))
    retired = uow.components.get(react.id or 0)
    assert retired.retired_in_version_id == result.version.id
    assert retired.is_retired
    [finding] = uow.findings.list()
    assert finding.component_id == react.id
    assert finding.status == FindingStatus.ACCEPTED
    assert result.removed == 1


def test_removed_component_without_findings_is_deleted() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    _upload(uow, application_id, _parsed(_REACT))
    _upload(uow, application_id, _parsed(_LODASH, label="1.1.0"))
    assert [c.name for c in uow.components.list_for_application(application_id)] == ["lodash"]


def test_reconcile_ignores_retired_components() -> None:
    uow = InMemoryUnitOfWork()
    application_id = _application(uow)
    _upload(uow, application_id, _parsed(_REACT))
    react = uow.components.list_for_application(application_id)[0]
    _finding_for(uow, react)
    _upload(uow, application_id, _parsed(_LODASH, label="1.1.0"))
    back = _upload(uow, application_id, _parsed(_REACT, _LODASH, label="1.2.0"))
    assert (back.added, back.kept, back.removed) == (1, 1, 0)
    live = [c for c in uow.components.list_for_application(application_id) if not c.is_retired]
    assert sorted(c.name for c in live) == ["lodash", "react"]
