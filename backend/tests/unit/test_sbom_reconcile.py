from app.application.sbom_reconcile import merge_duplicates, reconcile
from app.domain.inventory import Category, Component, Ecosystem
from app.domain.sbom import SbomEntry


def _entry(name: str, version: str, ecosystem: Ecosystem | None, *, direct: bool) -> SbomEntry:
    return SbomEntry(name, version, Category.LIBRARY, ecosystem, direct, None)


def _live(name: str, version: str, ecosystem: Ecosystem | None, component_id: int) -> Component:
    return Component(
        name,
        version,
        Category.LIBRARY,
        ecosystem,
        True,
        id=component_id,
        application_id=1,
        sbom_id=1,
    )


def test_merge_duplicates_keeps_one_and_any_direct() -> None:
    merged = merge_duplicates(
        [
            _entry("react", "18.2.0", Ecosystem.NPM, direct=False),
            _entry("lodash", "4.17.21", Ecosystem.NPM, direct=False),
            _entry("react", "18.2.0", Ecosystem.NPM, direct=True),
        ]
    )
    assert [(entry.name, entry.direct) for entry in merged] == [("react", True), ("lodash", False)]


def test_reconcile_treats_pypi_spelling_as_same() -> None:
    live = [
        _live("Jinja2", "3.1.4", Ecosystem.PYPI, 1),
        _live("typing_extensions", "4.12.0", Ecosystem.PYPI, 2),
    ]
    entries = [
        _entry("jinja2", "3.1.4", Ecosystem.PYPI, direct=True),
        _entry("typing-extensions", "4.12.0", Ecosystem.PYPI, direct=True),
    ]
    result = reconcile(live, entries)
    assert [component.id for component, _ in result.to_keep] == [1, 2]
    assert result.to_add == ()
    assert result.to_remove == ()


def test_reconcile_version_change_is_remove_and_add() -> None:
    result = reconcile(
        [_live("react", "18.2.0", Ecosystem.NPM, 1)],
        [_entry("react", "18.3.1", Ecosystem.NPM, direct=True)],
    )
    assert [component.id for component in result.to_remove] == [1]
    assert [entry.version for entry in result.to_add] == ["18.3.1"]
    assert result.to_keep == ()


def test_reconcile_distinguishes_ecosystems() -> None:
    result = reconcile(
        [_live("openssl", "3.0.11", None, 1)],
        [_entry("openssl", "3.0.11", Ecosystem.NPM, direct=True)],
    )
    assert len(result.to_remove) == 1
    assert len(result.to_add) == 1
