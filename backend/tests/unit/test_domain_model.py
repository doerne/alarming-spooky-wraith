from dataclasses import replace
from datetime import UTC, datetime

from app.domain.errors import (
    ComponentManagedBySbomError,
    ConflictError,
    DuplicateSbomVersionError,
    InvalidSbomError,
    InvalidValueError,
)
from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.sbom import SbomEntry, SbomVersion
from app.domain.vulnerability import (
    Finding,
    FindingStatus,
    ResolutionSource,
    RiskScore,
    Severity,
    is_valid_advisory_id,
)


def test_application_defaults_to_no_components() -> None:
    app = Application(name="Shop")
    assert app.components == []
    assert app.id is None


def test_component_carries_match_fields() -> None:
    component = Component(
        name="react",
        version="18.2.0",
        category=Category.LIBRARY,
        ecosystem=Ecosystem.NPM,
        direct=True,
    )
    assert component.ecosystem == Ecosystem.NPM
    assert component.direct is True


def test_finding_is_open_by_default() -> None:
    finding = Finding(
        advisory_id="CVE-2024-1",
        component_id=1,
        application_id=1,
        found_version="1.0.0",
        risk=RiskScore(value=98, level=Severity.KRITISCH, rationale="x"),
    )
    assert finding.status is FindingStatus.OPEN


def test_sbom_entry_without_ecosystem_is_unchecked() -> None:

    entry = SbomEntry(
        name="openssl",
        version="3.0.11",
        category=Category.LIBRARY,
        ecosystem=None,
        direct=True,
        purl="pkg:deb/debian/openssl@3.0.11",
    )
    assert entry.checked is False
    npm_entry = SbomEntry("react", "18.2.0", Category.LIBRARY, Ecosystem.NPM, True, None)
    assert npm_entry.checked is True


def test_component_defaults_to_manual_and_checked() -> None:
    component = Component(
        name="react",
        version="18.2.0",
        category=Category.LIBRARY,
        ecosystem=Ecosystem.NPM,
        direct=True,
    )
    assert component.sbom_id is None
    assert component.checked is True


def test_sbom_errors_have_expected_bases() -> None:

    assert issubclass(DuplicateSbomVersionError, ConflictError)
    assert issubclass(ComponentManagedBySbomError, ConflictError)
    assert issubclass(InvalidSbomError, InvalidValueError)


def test_sbom_version_counts_entries() -> None:
    version = SbomVersion(
        sbom_id=1,
        label="v1",
        uploaded_at=datetime(2026, 11, 21, tzinfo=UTC),
        serial_number=None,
        is_current=True,
        entries=(
            SbomEntry("react", "18.2.0", Category.LIBRARY, Ecosystem.NPM, True, None),
            SbomEntry("openssl", "3.0.11", Category.LIBRARY, None, False, None),
        ),
    )
    assert version.component_count == 2
    assert version.unchecked_count == 1


def test_advisory_id_rule() -> None:
    assert is_valid_advisory_id("CVE-2024-1")
    assert is_valid_advisory_id("GHSA-6q48-6c7w-9gw2")
    assert not is_valid_advisory_id("../etc")
    assert not is_valid_advisory_id("X" * 65)
    assert not is_valid_advisory_id("")


def _plain_finding(comment: str = "") -> Finding:
    return Finding(
        advisory_id="CVE-1",
        component_id=1,
        application_id=1,
        found_version="1.0",
        risk=RiskScore(value=50, level=Severity.MITTEL, rationale=""),
        comment=comment,
    )


def test_finding_with_note_appends_comment() -> None:
    assert _plain_finding().with_note("neu").comment == "neu"
    assert _plain_finding("alt").with_note("neu").comment == "alt\n\nneu"
    assert _plain_finding("alt").with_note("").comment == "alt"


def test_finding_reopened_clears_resolution() -> None:
    fixed = replace(
        _plain_finding(),
        status=FindingStatus.FIXED,
        resolved_at=datetime(2026, 11, 21, tzinfo=UTC),
        resolved_by=ResolutionSource.REPORTED,
        resolution="gemeldet",
    )
    reopened = fixed.reopened()
    assert (reopened.status, reopened.resolved_at, reopened.resolved_by, reopened.resolution) == (
        FindingStatus.OPEN,
        None,
        None,
        "",
    )
