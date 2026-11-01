"""Übersetzt Versionsbedingungen (GitHub, Composer, EUVD …) in OSV-Ereignisse.

Eine Bedingung wie ``>= 1.0, < 1.5`` wird zu ``introduced 1.0`` + ``fixed 1.5``;
``= 1.2`` oder eine nackte Version wird zur expliziten Version.
"""

import re

from app.domain.ports import RangeEvent

_TOKEN = re.compile(r"(>=|<=|==|!=|>|<|=)?\s*([^\s,<>=!]+)")
_FROM_START = RangeEvent("introduced", "0")
_UPPER_KIND = {"<": "fixed", "<=": "last_affected"}
_LOWER_OPERATORS = (">=", ">")
_EXACT_OPERATORS = ("", "=", "==")


def parse_constraint(text: str) -> tuple[tuple[RangeEvent, ...], tuple[str, ...]]:
    """Eine UND-verknüpfte Bedingung → (Ereignisse, explizite Versionen)."""
    lower: list[RangeEvent] = []
    upper: list[RangeEvent] = []
    exact: list[str] = []
    for operator, version in _TOKEN.findall(text):
        if operator in _LOWER_OPERATORS:
            lower.append(RangeEvent("introduced", version))
        elif operator in _UPPER_KIND:
            upper.append(RangeEvent(_UPPER_KIND[operator], version))
        elif operator in _EXACT_OPERATORS:
            exact.append(version)
    if not lower and not upper:
        return (), tuple(exact)
    return (*(lower or [_FROM_START]), *upper), ()


def parse_alternatives(text: str, separator: str) -> tuple[tuple[RangeEvent, ...], tuple[str, ...]]:
    """ODER-verknüpfte Bedingungen (z. B. Composer ``|``) zusammenführen."""
    events: list[RangeEvent] = []
    versions: list[str] = []
    for alternative in text.split(separator):
        alternative_events, alternative_versions = parse_constraint(alternative)
        events.extend(alternative_events)
        versions.extend(alternative_versions)
    return tuple(events), tuple(versions)
