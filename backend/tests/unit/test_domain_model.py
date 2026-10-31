from app.domain.inventory import Application, Category, Component, Ecosystem
from app.domain.vulnerability import Finding, FindingStatus, RiskScore, Severity


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
