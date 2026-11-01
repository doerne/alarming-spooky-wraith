from app.application.component_matching import ComponentMatcher, normalize_package_name
from app.domain.inventory import Category, Component, Ecosystem
from app.domain.ports import AffectedPackage, RangeEvent, SourceVuln
from app.domain.sources import MatchScope
from app.infrastructure.univers_matcher import UniversVersionMatcher

_MATCHER = ComponentMatcher(UniversVersionMatcher())
_RANGE = (RangeEvent("introduced", "0"), RangeEvent("fixed", "2.0.0"))


def _component(name: str, ecosystem: Ecosystem | None, version: str = "1.0.0") -> Component:
    return Component(
        name=name, version=version, category=Category.LIBRARY, ecosystem=ecosystem, direct=True
    )


def _vuln(*affected: AffectedPackage) -> SourceVuln:
    return SourceVuln(
        source_key="demo",
        id="CVE-2024-1",
        aliases=[],
        summary="s",
        details="",
        cvss_base=None,
        fixed_version=None,
        references=[],
        url="https://example.org",
        affected=affected,
    )


def test_package_scope_requires_same_ecosystem() -> None:
    vuln = _vuln(AffectedPackage("PyPI", "requests", _RANGE))
    assert _MATCHER.matches(_component("requests", Ecosystem.PYPI), vuln, MatchScope.PACKAGE)
    assert not _MATCHER.matches(_component("requests", Ecosystem.NPM), vuln, MatchScope.PACKAGE)


def test_pypi_name_normalization() -> None:
    assert normalize_package_name("PyPI", "Django_Rest.Framework") == "django-rest-framework"
    vuln = _vuln(AffectedPackage("PyPI", "django-rest-framework", _RANGE))
    component = _component("Django_Rest-Framework", Ecosystem.PYPI)
    assert _MATCHER.matches(component, vuln, MatchScope.PACKAGE)


def test_version_outside_range_does_not_match() -> None:
    vuln = _vuln(AffectedPackage("npm", "react", _RANGE))
    component = _component("react", Ecosystem.NPM, version="2.0.0")
    assert not _MATCHER.matches(component, vuln, MatchScope.PACKAGE)


def test_product_without_ranges_does_not_match() -> None:
    vuln = _vuln(AffectedPackage(None, "mariadb"))
    assert not _MATCHER.matches(_component("MariaDB", None), vuln, MatchScope.PRODUCT)


def test_product_matches_case_insensitive_with_range() -> None:
    vuln = _vuln(AffectedPackage(None, "mariadb", _RANGE))
    assert _MATCHER.matches(_component("MariaDB", None), vuln, MatchScope.PRODUCT)


def test_product_name_must_match_exactly() -> None:
    vuln = _vuln(AffectedPackage(None, "mariadb-connector", _RANGE))
    assert not _MATCHER.matches(_component("MariaDB", None), vuln, MatchScope.PRODUCT)


def test_name_scope_matches_without_version() -> None:
    vuln = _vuln(AffectedPackage(None, "django"))
    component = _component("Django", Ecosystem.PYPI, version="99.0")
    assert _MATCHER.matches(component, vuln, MatchScope.NAME)
