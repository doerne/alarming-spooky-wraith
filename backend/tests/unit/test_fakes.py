from app.domain.vulnerability import Finding, FindingStatus, RiskScore, Severity
from tests.fakes import InMemoryFindingRepository


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
