"""Fachliche Kennzeichen von CVE-Issues: Label und Marker (Rückkanal-Zuordnung)."""

import re

ISSUE_LABEL = "security"
MARKER_PREFIX = "cve-radar:"
_MARKER_PATTERN = re.compile(rf"<!-- {MARKER_PREFIX}application=\d+;advisory=[A-Za-z0-9_-]+ -->")


def issue_marker(application_id: int, advisory_id: str) -> str:
    """Feste Kennung im Issue-Text; Rückkanäle ordnen Issues darüber zu."""
    return f"<!-- {MARKER_PREFIX}application={application_id};advisory={advisory_id} -->"


def find_markers(text: str) -> list[str]:
    """Alle gültigen Marker-Zeilen eines Textes."""
    return _MARKER_PATTERN.findall(text)
