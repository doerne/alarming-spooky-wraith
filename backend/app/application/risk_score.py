"""Risk Score aus dem CVSS-Basisscore (Stufe 1 der Umsetzung).

Spaetere Stufen beziehen EPSS, KEV, Fix-Verfuegbarkeit und direkt/transitiv ein.
Die Gewichte liegen hier bewusst als reine Funktion, damit sie testbar bleiben.
"""

from app.domain.vulnerability import RiskScore, Severity

_KRITISCH = 90
_HOCH = 70
_MITTEL = 40


def _level_for(value: int) -> Severity:
    if value >= _KRITISCH:
        return Severity.KRITISCH
    if value >= _HOCH:
        return Severity.HOCH
    if value >= _MITTEL:
        return Severity.MITTEL
    return Severity.NIEDRIG


def compute_risk_score(cvss_base: float | None) -> RiskScore:
    """Berechnet den Risk Score. Ohne CVSS bleibt der Wert 0 (nichts geraten)."""
    if cvss_base is None:
        return RiskScore(
            value=0,
            level=Severity.NIEDRIG,
            rationale="kein CVSS verfuegbar; Bewertung folgt bei Anreicherung",
        )
    value = max(0, min(100, round(cvss_base * 10)))
    return RiskScore(
        value=value,
        level=_level_for(value),
        rationale=f"CVSS-Basisscore {cvss_base} -> {value}/100",
    )
