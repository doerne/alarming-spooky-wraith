import pytest

from app.domain.ports import AffectedPackage, RangeEvent
from app.infrastructure.univers_matcher import UniversVersionMatcher

_MATCHER = UniversVersionMatcher()


def _package(*events: tuple[str, str], versions: tuple[str, ...] = ()) -> AffectedPackage:
    return AffectedPackage(
        ecosystem=None,
        name="pkg",
        events=tuple(RangeEvent(kind, version) for kind, version in events),
        versions=versions,
    )


def test_npm_range_affected() -> None:
    package = _package(("introduced", "0"), ("fixed", "18.2.1"))
    assert _MATCHER.is_affected("npm", "18.2.0", package) is True
    assert _MATCHER.is_affected("npm", "18.2.1", package) is False


def test_pypi_pep440() -> None:
    package = _package(("introduced", "1.0"), ("fixed", "2.0"))
    assert _MATCHER.is_affected("PyPI", "2.0rc1", package) is True
    assert _MATCHER.is_affected("PyPI", "0.9", package) is False


def test_last_affected_inclusive() -> None:
    package = _package(("introduced", "1.0.0"), ("last_affected", "1.4.0"))
    assert _MATCHER.is_affected("crates.io", "1.4.0", package) is True
    assert _MATCHER.is_affected("crates.io", "1.4.1", package) is False


def test_explicit_versions_list() -> None:
    package = _package(versions=("4.1.0", "4.1.1"))
    assert _MATCHER.is_affected("RubyGems", "4.1.1", package) is True
    assert _MATCHER.is_affected("RubyGems", "4.1.2", package) is False


def test_product_versions_compare_numerically() -> None:
    package = _package(("introduced", "11.4.0"), ("fixed", "11.4.10"))
    assert _MATCHER.is_affected(None, "11.4.9", package) is True
    assert _MATCHER.is_affected(None, "11.4.10", package) is False


def test_reopened_range_after_fix() -> None:
    package = _package(("introduced", "1.0"), ("fixed", "1.5"), ("introduced", "2.0"))
    assert _MATCHER.is_affected("Maven", "1.6", package) is False
    assert _MATCHER.is_affected("Maven", "2.1", package) is True


@pytest.mark.parametrize("version", ["latest", "1.x", ""])
def test_unparseable_version_is_not_affected(version: str) -> None:
    package = _package(("introduced", "0"), ("fixed", "18.2.1"))
    assert _MATCHER.is_affected("npm", version, package) is False


def test_unparseable_event_is_ignored() -> None:
    package = _package(("introduced", "0"), ("fixed", "not-a-version"))
    assert _MATCHER.is_affected("npm", "1.0.0", package) is False
