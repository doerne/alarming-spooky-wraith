"""Kleine Namens- und Zugangsdaten-Helfer für Quellen."""

import re

from app.domain.errors import SourceAccessError

_PYPI_SEPARATORS = re.compile(r"[-_.]+")
MISSING_KEY = "API-Key fehlt"


def normalize_pypi(name: str) -> str:
    return _PYPI_SEPARATORS.sub("-", name.lower())


def require_key(api_key: str | None) -> str:
    if not api_key:
        raise SourceAccessError(MISSING_KEY)
    return api_key


def split_key(api_key: str | None, expected: str) -> tuple[str, str]:
    """Zerlegt einen Key im Format ``<a>:<b>``; ``expected`` nennt das Format."""
    first, separator, second = require_key(api_key).partition(":")
    if not separator or not first or not second:
        raise SourceAccessError(f"API-Key hat nicht das Format {expected}")
    return first, second
