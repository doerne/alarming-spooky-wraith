import pytest
from app.application.risk_score import compute_risk_score

from app.domain.vulnerability import Severity


@pytest.mark.parametrize(
    ("base", "value", "level"),
    [
        (9.8, 98, Severity.KRITISCH),
        (7.5, 75, Severity.HOCH),
        (5.0, 50, Severity.MITTEL),
        (1.5, 15, Severity.NIEDRIG),
    ],
)
def test_score_from_cvss(base: float, value: int, level: Severity) -> None:
    result = compute_risk_score(base)
    assert result.value == value
    assert result.level == level


def test_no_cvss_is_niedrig_zero() -> None:
    result = compute_risk_score(None)
    assert result.value == 0
    assert result.level == Severity.NIEDRIG
    assert "kein CVSS" in result.rationale
